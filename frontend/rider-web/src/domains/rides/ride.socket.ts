import { useRideStore } from "./ride.store";

let socket: WebSocket | null = null;

export function startRideSocket(rideId: number) {
  if (socket) return;

  socket = new WebSocket(`ws://localhost/ws/rides/${rideId}/`);

  socket.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.status) {
      useRideStore.getState().setStatus(data.status);
    }

    if (data.driver_location) {
      useRideStore
        .getState()
        .setDriverLocation(
          data.driver_location.lat,
          data.driver_location.lng
        );
    }
  };
}

export function stopRideSocket() {
  socket?.close();
  socket = null;
}
