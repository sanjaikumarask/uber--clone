import axios from "axios";
import { useAuthStore } from "../store/auth.store";

const http = axios.create({
  baseURL: "http://localhost:8000/api",
});

http.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default http;
