import { create } from "zustand";
import { Storage } from "../../services/storage";

interface User {
    id: number;
    phone: string;
    role: "rider" | "driver" | "admin";
    first_name: string;
    last_name: string;
}

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    login: (user: User, accessToken: string, refreshToken: string) => Promise<void>;
    logout: () => Promise<void>;
    loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
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
            // Typically fetch /me here to validate
            set({ isAuthenticated: true });
        }
    },
}));
