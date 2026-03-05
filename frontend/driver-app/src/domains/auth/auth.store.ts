import { create } from "zustand";
import { Storage } from "../../services/storage";

interface User {
    id: number;
    phone: string;
    role: "rider" | "driver" | "admin";
    first_name: string;
    last_name: string;
    is_verified?: boolean;
    completed_rides?: number;
    avg_rating?: string | number;
    level?: string;
}

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    login: (user: User, accessToken: string, refreshToken: string) => Promise<void>;
    logout: () => Promise<void>;
    loadUser: () => Promise<void>;
    syncUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
    user: null,
    isAuthenticated: false,

    login: async (user, access, refresh) => {
        await Storage.setToken(access);
        await Storage.setRefreshToken(refresh);
        set({ user, isAuthenticated: true });
    },

    logout: async () => {
        await Storage.clear();
        set({ user: null, isAuthenticated: false });
    },

    loadUser: async () => {
        const token = await Storage.getToken();
        if (token) {
            try {
                const { api } = await import("../../services/api");
                const { data } = await api.get("users/me/");
                set({ user: data, isAuthenticated: true });
            } catch (err) {
                console.error("Failed to load user:", err);
                await Storage.clear();
                set({ user: null, isAuthenticated: false });
            }
        }
    },

    syncUser: async () => {
        if (!get().isAuthenticated) return;
        try {
            const { api } = await import("../../services/api");
            const { data } = await api.get("users/me/");
            set({ user: data });
        } catch (err) {
            console.error("Sync user failed:", err);
        }
    }
}));
