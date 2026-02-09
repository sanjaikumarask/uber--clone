let socket: WebSocket | null = null;

export const connectDriverSocket = () => {
  if (socket) return;

  socket = new WebSocket(import.meta.env.VITE_DRIVER_SOCKET_URL);

  socket.onopen = () => {
    console.log("Driver socket connected");
  };

  socket.onclose = () => {
    console.log("Driver socket disconnected");
    socket = null;
  };
};

export const disconnectDriverSocket = () => {
  if (socket) {
    socket.close();
    socket = null;
  }
};
