export function createRideSocket(rideId: number) {
  const token = localStorage.getItem("access");
  if (!rideId || !token) return null;

  return new WebSocket(
    `ws://localhost:8000/ws/rides/${rideId}/?token=${token}`
  );
}
