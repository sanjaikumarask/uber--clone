import { useEffect, useRef } from "react";
import AppRoutes from "./routes";
import { getActiveRide } from "../services/ride.service";
import { useAuthStore } from "../store/auth.store";
import { useRideStore } from "../store/ride.store";
import { useRideSocket } from "../realtime/useRideSocket";

export default function App() {
  const token = useAuthStore((s) => s.token);
  const setRide = useRideStore((s) => s.setRide);

  const initialized = useRef(false);

  // 🔒 hydrate active ride ONCE
  useEffect(() => {
    if (!token) return;
    if (initialized.current) return;

    initialized.current = true;

    getActiveRide()
      .then((ride) => {
        if (ride?.ride_id) {
          setRide(ride.ride_id, ride.status);
        }
      })
      .catch(() => {});
  }, [token, setRide]);

  // 🔥 SINGLE websocket connection
  useRideSocket();

  return <AppRoutes />;
}


