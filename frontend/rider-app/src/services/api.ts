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

// Request Interceptor: Attach Token
api.interceptors.request.use(async (config) => {
    const token = await Storage.getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response Interceptor: Handle Errors
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid
            await Storage.clear();
            // TODO: Navigate to login
        }
        return Promise.reject(error);
    }
);
