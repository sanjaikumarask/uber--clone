import axios from "axios";
import { Storage } from "./storage";
import { Platform } from "react-native";

// For physical device, use your computer's actual IP address
// This is more reliable than ADB reverse for some devices
const YOUR_COMPUTER_IP = "192.169.1.137";

const HOST = YOUR_COMPUTER_IP;
export const API_URL = `http://${HOST}:8000/api`;
export const WS_URL = `ws://${HOST}:8000/ws`;

console.log("📡 API Configuration:");
console.log("   Platform:", Platform.OS);
console.log("   Host:", HOST);
console.log("   API URL:", API_URL);

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

api.interceptors.request.use(async (config) => {
    const token = await Storage.getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        // Add refresh token logic here if needed
        if (error.response?.status === 401) {
            // Logic to clear token or refresh
            // await Storage.clear();
        }
        return Promise.reject(error);
    }
);
