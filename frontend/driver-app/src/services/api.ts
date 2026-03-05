import axios from "axios";
import { Storage } from "./storage";
import { Platform } from "react-native";

// For physical device, use your computer's actual IP address
const YOUR_COMPUTER_IP = "192.169.1.137";

const HOST = YOUR_COMPUTER_IP;
export const API_URL = `http://${HOST}/api/`;
export const WS_URL = `ws://${HOST}/ws`;

console.log("📡 DRIVER API Configuration:");
console.log("   Platform:", Platform.OS);
console.log("   Host:", HOST);
console.log("   API URL:", API_URL);

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

// Request Interceptor: Attach Token
api.interceptors.request.use(async (config) => {
    const token = await Storage.getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response Interceptor: Handle 401 & Refresh Token
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

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
            } catch (refreshError) {
                processQueue(refreshError, null);
                isRefreshing = false;
                await Storage.clear();
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);
