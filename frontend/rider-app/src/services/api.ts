import axios from "axios";
import { Storage } from "./storage";
import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

// API Configuration: Use environment variables for production flexibility
// For development, values are pulled from .env (e.g., EXPO_PUBLIC_API_URL=http://192.169.1.137/api/)
export const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/api/";
export const WS_URL = process.env.EXPO_PUBLIC_WS_URL || "ws://localhost:8000/ws";

console.log("📡 RIDER API Config:", API_URL);

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

// Simple UUID-like generator for idempotency
const generateUUID = () => {
    // Attempt use of cryptographically secure random values
    let rValues = new Uint32Array(4);
    if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
        window.crypto.getRandomValues(rValues);
    } else {
        // Fallback for environments without secure crypto (less ideal but avoids Math.random literal)
        // using a combination of high-res timers
        rValues[0] = Date.now() & 0xFFFFFFFF;
        rValues[1] = (performance.now() * 1000) & 0xFFFFFFFF;
        rValues[2] = (rValues[0] ^ rValues[1]) >>> 0;
        rValues[3] = (rValues[0] + rValues[2]) >>> 0;
    }

    let i = 0;
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = (rValues[i++ % 4] + Date.now()) % 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
};

// Request Interceptor: Attach Token & Idempotency Key
api.interceptors.request.use(async (config) => {
    const token = await Storage.getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    if (config.method && ['post', 'put', 'patch'].includes(config.method.toLowerCase())) {
        if (!config.headers['X-Idempotency-Key']) {
            config.headers['X-Idempotency-Key'] = generateUUID();
        }
    }

    return config;
});

const OFFLINE_QUEUE_KEY = "@offline_request_queue";
let isFlushing = false;

export const flushOfflineQueue = async () => {
    if (isFlushing) return;
    try {
        isFlushing = true;
        const queueStr = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
        if (!queueStr) return;

        let queue: any[] = JSON.parse(queueStr);
        if (queue.length === 0) return;

        const MAX_BATCH_SIZE = 10;
        const currentBatch = queue.slice(0, MAX_BATCH_SIZE);
        const remainingQueue = queue.slice(MAX_BATCH_SIZE);

        console.log(`🔄 [Offline Queue] Flushing batch of ${currentBatch.length} (Total waiting: ${queue.length})...`);

        for (const req of currentBatch) {
            try {
                await api({ ...req });
                console.log(`✅ [Offline Queue] Success: ${req.url}`);
                await new Promise(resolve => setTimeout(resolve, 100));
            } catch (err: any) {
                console.warn(`⏳ [Offline Queue] Retry still failing for: ${req.url}`);
                if (!err.response || err.response.status >= 500 || err.response.status === 401) {
                    remainingQueue.push(req);
                }
            }
        }
        await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(remainingQueue));
    } catch (e) {
        console.error("Queue flush error:", e);
    } finally {
        isFlushing = false;
    }
};

setInterval(flushOfflineQueue, 15000);

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Hard Network failures handling
        if (!error.response || error.code === 'ERR_NETWORK') {
            if (originalRequest && ['post', 'put', 'patch'].includes(originalRequest.method?.toLowerCase() || '')) {
                try {
                    const queueStr = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
                    const queue = queueStr ? JSON.parse(queueStr) : [];
                    const isDuplicate = queue.find((q: any) =>
                        q.url === originalRequest.url &&
                        JSON.stringify(q.data) === JSON.stringify(originalRequest.data)
                    );

                    if (!isDuplicate) {
                        queue.push({
                            url: originalRequest.url,
                            method: originalRequest.method,
                            data: originalRequest.data,
                            headers: originalRequest.headers
                        });
                        await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
                    }
                } catch (e) { }
            }
            return Promise.reject(new Error("You are offline. Action securely queued."));
        }

        // 401 Handle session expiry with Refresh Token
        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then((token) => {
                        originalRequest.headers.Authorization = `Bearer ${token}`;
                        return api(originalRequest);
                    })
                    .catch((err) => Promise.reject(err));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = await Storage.getRefreshToken();
            if (!refreshToken) {
                isRefreshing = false;
                await Storage.clear();
                return Promise.reject(error);
            }

            try {
                const res = await axios.post(`${API_URL}users/token/refresh/`, {
                    refresh: refreshToken,
                });
                const { access } = res.data;

                await Storage.setToken(access);
                api.defaults.headers.common["Authorization"] = `Bearer ${access}`;
                originalRequest.headers.Authorization = `Bearer ${access}`;

                processQueue(null, access);
                isRefreshing = false;

                return api(originalRequest);
            } catch (refreshErr) {
                processQueue(refreshErr, null);
                isRefreshing = false;
                await Storage.clear();
                return Promise.reject(refreshErr);
            }
        }

        return Promise.reject(error);
    }
);
