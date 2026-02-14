import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

// ===============================
// REQUEST INTERCEPTOR (JWT)
// ===============================
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ===============================
// RESPONSE INTERCEPTOR (401)
// ===============================
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // ⚠️ DO NOT clear user unless token is truly invalid
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);
