let socket: WebSocket | null = null;

export function connectRideSocket(rideId: number, token: string) {
  if (socket) return socket; // 🔒 singleton

  socket = new WebSocket(
    `ws://localhost:8000/ws/rides/${rideId}/?token=${token}`
  );

  socket.onopen = () => console.log("Ride socket connected");
  socket.onclose = () => {
    console.log("Ride socket closed");
    socket = null;
  };
  socket.onerror = (e) => console.error("Ride socket error", e);

  return socket;
}
