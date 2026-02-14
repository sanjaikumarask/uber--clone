import { useRideStore } from "../rides/ride.store";

let socket: WebSocket | null = null;

export function startTrackingSocket(rideId: number) {
  if (socket || !rideId) return;

  const token = localStorage.getItem("access");
  if (!token) {
    console.error("No access token for WS");
    return;
  }

  const wsUrl = `ws://${window.location.host}/ws/rides/${rideId}/?token=${token}`;
  console.log("🔌 Connecting WS:", wsUrl);

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("✅ WS connected");
  };

  socket.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    const { payload, type } = msg;

    console.log("📡 WS event:", type, payload);

    if (payload?.driver_location) {
      useRideStore.getState().setDriverLocation(
        payload.driver_location.lat,
        payload.driver_location.lng
      );
    }

    if (payload?.status) {
      useRideStore.getState().setStatus(payload.status);
    }
  };

  socket.onerror = (err) => {
    console.error("❌ WS error", err);
  };

  socket.onclose = () => {
    console.warn("⚠️ WS closed");
    socket = null;
  };
}

export function stopTrackingSocket() {
  if (socket) {
    socket.close();
    socket = null;
  }
}
