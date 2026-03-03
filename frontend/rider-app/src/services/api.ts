import axios from "axios";
import { Storage } from "./storage";
import { Platform } from "react-native";

// Change this to your computer's IP address
// Use '10.0.2.2' for Android Emulator, or your local LAN IP for physical device
const YOUR_COMPUTER_IP = "192.169.1.137";

const HOST = YOUR_COMPUTER_IP;
export const API_URL = `http://${HOST}/api`;
export const WS_URL = `ws://${HOST}/ws`;

console.log("📡 RIDER API Config:", API_URL);

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Simple UUID generator for idempotency
const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
};

// Request Interceptor: Attach Token & Idempotency Key
api.interceptors.request.use(async (config) => {
    const token = await Storage.getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    // Attach Idempotency Header for Mutations
    if (config.method && ['post', 'put', 'patch'].includes(config.method.toLowerCase())) {
        if (!config.headers['X-Idempotency-Key']) {
            config.headers['X-Idempotency-Key'] = generateUUID();
        }
    }

    return config;
});

// Response Interceptor: Handle Errors
import AsyncStorage from "@react-native-async-storage/async-storage";

const OFFLINE_QUEUE_KEY = "@offline_request_queue";
let isFlushing = false;

// 🔴 Auto-Retry Unsent Requests with Backpressure Control
export const flushOfflineQueue = async () => {
    if (isFlushing) return;
    try {
        isFlushing = true;
        const queueStr = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
        if (!queueStr) return;

        let queue: any[] = JSON.parse(queueStr);
        if (queue.length === 0) return;

        // ✅ Backpressure: Process max 5-10 requests at a time to avoid DDOSing the server
        const MAX_BATCH_SIZE = 10;
        const currentBatch = queue.slice(0, MAX_BATCH_SIZE);
        const remainingQueue = queue.slice(MAX_BATCH_SIZE);

        console.log(`🔄 [Offline Queue] Flushing batch of ${currentBatch.length} (Total waiting: ${queue.length})...`);

        for (const req of currentBatch) {
            try {
                // ✅ USE API INSTANCE: Ensures interceptors (token refresh) are applied
                await api({ ...req });
                console.log(`✅ [Offline Queue] Success: ${req.url}`);

                // Add tiny 100ms artificial delay to prevent socket flooding
                await new Promise(resolve => setTimeout(resolve, 100));
            } catch (err: any) {
                console.warn(`⏳ [Offline Queue] Retry still failing for: ${req.url}`);
                // ✅ PREVENT DATA LOSS: If 401 (Unauthorized/Expired), keep in queue!
                // Don't discard until the user successfully logs back in and retry succeeds.
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
        // Detect Hard Network failures
        if (!error.response || error.code === 'ERR_NETWORK') {
            const config = error.config;
            if (config && ['post', 'put', 'patch'].includes(config.method?.toLowerCase() || '')) {
                try {
                    const queueStr = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
                    const queue = queueStr ? JSON.parse(queueStr) : [];

                    // Prevent duplicate queuing of exact identical API calls targeting same location
                    const isDuplicate = queue.find((q: any) =>
                        q.url === config.url &&
                        JSON.stringify(q.data) === JSON.stringify(config.data)
                    );

                    if (!isDuplicate) {
                        queue.push({
                            url: config.url,
                            method: config.method,
                            data: config.data,
                            headers: config.headers
                        });
                        await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
                        console.log(`📉 [Offline Mode] Request queued securely: ${config.url}`);
                    }
                } catch (e) { }
            }
            return Promise.reject(new Error("You are offline. Action securely queued."));
        }

        if (error.response?.status === 401) {
            // Token expired or invalid
            await Storage.clear();
            console.error("Token Expired - session dropping");
        }
        return Promise.reject(error);
    }
);

