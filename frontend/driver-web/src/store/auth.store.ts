import { create } from "zustand";
import { authStorage } from "../utils/storage";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: authStorage.get(),
  isAuthenticated: !!authStorage.get(),

  login: (token) => {
    authStorage.set(token);
    set({ token, isAuthenticated: true });
  },

  logout: () => {
    authStorage.clear();
    set({ token: null, isAuthenticated: false });
  },
}));
