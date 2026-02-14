import { create } from "zustand";

interface User {
  id: number;
  phone: string;
  role: "rider" | "driver" | "admin";
  first_name: string;
  last_name: string;
}

interface AuthState {
  user: User | null;
  access: string | null;
  refresh: string | null;

  login: (data: {
    access: string;
    refresh: string;
    user: User;
  }) => void;

  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  access: null,
  refresh: null,

  login(data) {
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);

    set({
      user: data.user,
      access: data.access,
      refresh: data.refresh,
    });
  },

  logout() {
    localStorage.clear();
    set({ user: null, access: null, refresh: null });
  },
}));
