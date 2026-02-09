import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { useDriverSocket } from "./realtime/driverSocket";

const Root = () => {
  useDriverSocket();
  return <App />;
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
