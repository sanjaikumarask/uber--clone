import { useEffect, useRef } from "react";
import { useRideStore } from "../store/ride.store";
import { useAuthStore } from "../store/auth.store";

export function useRideSocket() {
  const rideId = useRideStore((s) => s.rideId);
  const updateStatus = useRideStore((s) => s.updateStatus);
  const updateDriverLocation = useRideStore((s) => s.updateDriverLocation);
  const token = useAuthStore((s) => s.token);

  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!rideId || !token) return;
    if (socketRef.current) return; // 🔒 prevent double connect

    const ws = new WebSocket(
      `ws://localhost:8000/ws/rides/${rideId}/?token=${token}`
    );

    socketRef.current = ws;

    ws.onopen = () => {
      console.log("Ride socket connected");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "STATUS_UPDATE") {
        updateStatus(data.status);
      }

      if (data.type === "DRIVER_LOCATION") {
        updateDriverLocation(data.lat, data.lng);
      }
    };

    ws.onerror = (e) => {
      console.error("Ride socket error", e);
    };

    ws.onclose = () => {
      console.log("Ride socket closed");
      socketRef.current = null;
    };

    return () => {
      // 🔥 DO NOT close immediately in dev StrictMode
      // Let backend decide
    };
  }, [rideId, token, updateStatus, updateDriverLocation]);
}
