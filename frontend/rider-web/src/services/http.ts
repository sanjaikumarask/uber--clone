// src/services/http.ts
import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

// ============================
// REQUEST — Attach JWT token
// ============================
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============================
// RESPONSE — Handle errors
// ============================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail: string = error.response?.data?.detail || "";

    // 401 — Token expired or missing → go to login
    if (status === 401) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }

    // 403 "Rider access only" — Driver account used on rider app → redirect
    if (status === 403 && detail.toLowerCase().includes("rider access only")) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user");
      alert("⚠️ You are logged in as a Driver. Please log in with your Rider account.");
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);
