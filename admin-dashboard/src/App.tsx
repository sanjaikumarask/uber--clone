import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import Drivers from "./pages/Drivers";
import Payments from "./pages/Payments";
import LiveMap from "./pages/LiveMap";
import AdminRides from "./pages/AdminRides";
import Login from "./pages/Login";

export default function App() {
  return (
    <BrowserRouter basename="/dashboard">
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* PROTECTED ADMIN ROUTES */}
        <Route element={<Layout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/drivers" element={<Drivers />} />
          <Route path="/rides" element={<AdminRides />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/live-map" element={<LiveMap />} />
        </Route>

        {/* FALLBACK */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
