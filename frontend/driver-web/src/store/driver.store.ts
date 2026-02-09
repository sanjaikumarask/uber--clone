import { useEffect } from "react";
import { useAuthStore } from "../store/auth.store";

let socket: WebSocket | null = null;

export function connectDriverSocket(token: string) {
  if (socket) return;

  socket = new WebSocket(
    `${import.meta.env.VITE_WS_BASE_URL}?token=${token}`
  );

  socket.onopen = () => console.log("Driver socket connected");
  socket.onclose = () => {
    socket = null;
    console.log("Driver socket closed");
  };
}

export function useDriverSocket() {
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (token) connectDriverSocket(token);
    return () => socket?.close();
  }, [token]);
}
