import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AuthGuard from "./auth/AuthGuard";
import DriverLayout from "./layouts/DriverLayout";

import Login from "./pages/driver/Login";
import Home from "./pages/driver/Home";
import RideRequest from "./pages/driver/RideRequest";
import Arrived from "./pages/driver/Arrived";
import InRide from "./pages/driver/InRide";
import RideCompleted from "./pages/driver/RideCompleted";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<AuthGuard />}>
          <Route element={<DriverLayout />}>
            <Route path="/driver" element={<Navigate to="/driver/home" replace />} />
            <Route path="/driver/home" element={<Home />} />
            <Route path="/driver/ride-request" element={<RideRequest />} />
            <Route path="/driver/arrived" element={<Arrived />} />
            <Route path="/driver/in-ride" element={<InRide />} />
            <Route path="/driver/ride-completed" element={<RideCompleted />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
