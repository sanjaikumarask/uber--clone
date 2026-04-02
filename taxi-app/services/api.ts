import axios from "axios";
import { Storage } from "./storage";

// 🌐 API Configuration
// Use your machine's local IP (e.g., http://192.168.1.10:8000/api) for physical device testing
const envUrl = process.env.EXPO_PUBLIC_API_URL;
const envWsUrl = process.env.EXPO_PUBLIC_WS_URL;
console.log("[AXIOS] ENV API URL detected:", !!envUrl, envUrl);

const rawApiUrl = envUrl || "http://10.0.2.2/api/";
const rawWsUrl = envWsUrl || "ws://10.0.2.2/ws/";
export const API_URL = rawApiUrl.endsWith("/") ? rawApiUrl : `${rawApiUrl}/`;
export const WS_URL = rawWsUrl.endsWith("/") ? rawWsUrl : `${rawWsUrl}/`;

console.log("[AXIOS] Effective BaseURL:", API_URL);

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Request Interceptor: Attach JWT Token & Idempotency Key
api.interceptors.request.use(async (config) => {
    try {
        const token = await Storage.getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    } catch (e) {
        console.warn("SecureStore Token read skipped via catch:", e);
    }

    // Add Idempotency key for mutations (POST/PUT/PATCH) to prevent double-processing
    if (config.method && ['post', 'put', 'patch'].includes(config.method.toLowerCase())) {
        config.headers['X-Idempotency-Key'] = Math.random().toString(36).substring(7);
    }

    return config;
});

// Response Interceptor: Handle Token Expiry
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        const status = error.response?.status;

        // 🛡️ Nginx 502/503/504 Cleanup: Don't let raw HTML hit the components
        if ([502, 503, 504].includes(status)) {
            error.response.data = { detail: "Server is temporarily unavailable. Please try again in a few moments." };
        }

        if (status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            const refreshToken = await Storage.getRefreshToken();
            
            if (refreshToken) {
                try {
                    const res = await axios.post(`${API_URL}users/token/refresh/`, {
                        refresh: refreshToken,
                    });
                    const { access } = res.data;
                    await Storage.setToken(access);
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                    return api(originalRequest);
                } catch (refreshErr) {
                    await Storage.clear();
                }
            }
        }
        return Promise.reject(error);
    }
);

// 🚀 CENTRALIZED APP FEATURES HELPER
export const apiActions = {
    // 👤 Profile & Setup
    getMe: () => api.get('users/me/'),
    updateProfile: (data: any) => api.patch('users/me/', data),
    updatePushToken: (token: string) => api.post('users/push-token/update/', { token }),

    // 💼 Wallet & Payments
    getWallet: () => api.get('users/wallet/'),
    getHistory: () => api.get('users/history/'),

    // 📍 Addresses
    getAddresses: () => api.get('users/addresses/'),
    saveAddress: (data: any) => api.post('users/addresses/', data),
    deleteAddress: (id: number) => api.delete(`users/addresses/${id}/`),

    // 🎁 Offers & Referrals
    getOffers: () => api.get('offers/'),
    getReferral: () => api.get('users/referral/'),

    // 🎧 Support & Complaints
    getFAQs: () => api.get('users/content/faqs/'),
    getAboutUs: () => api.get('users/content/about-us/'),
    createComplaint: (data: { ride_id?: number, reason: string, description: string }) => 
        api.post('users/complaint/', data),

    // 🛡️ Auth
    deleteAccount: () => api.delete('users/delete-account/'),
};

