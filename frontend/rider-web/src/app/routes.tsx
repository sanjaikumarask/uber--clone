import { Routes, Route, Navigate } from "react-router-dom";
import RequireAuth from "./RequireAuth";
import RideGuard from "./RideGuard";

import Login from "../pages/Login";
import Home from "../pages/Home";
import BookRide from "../pages/BookRide";
import RideSearching from "../pages/RideSearching";
import RideTracking from "../pages/RideTracking";

export default function AppRoutes() {
  return (
    <Routes>
      {/* =======================
          DEFAULT
      ======================= */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* =======================
          PUBLIC
      ======================= */}
      <Route path="/login" element={<Login />} />

      {/* =======================
          AUTHENTICATED (NO RIDE STATE)
      ======================= */}
      <Route
        path="/home"
        element={
          <RequireAuth>
            <Home />
          </RequireAuth>
        }
      />

      <Route
        path="/book"
        element={
          <RequireAuth>
            <BookRide />
          </RequireAuth>
        }
      />

      {/* =======================
          RIDE FLOW (STRICT)
      ======================= */}
      <Route
        path="/ride/searching"
        element={
          <RequireAuth>
            <RideGuard allow={["SEARCHING"]}>
              <RideSearching />
            </RideGuard>
          </RequireAuth>
        }
      />

      <Route
        path="/ride/tracking"
        element={
          <RequireAuth>
            <RideGuard allow={["ASSIGNED", "ARRIVED", "ONGOING"]}>
              <RideTracking />
            </RideGuard>
          </RequireAuth>
        }
      />

      {/* =======================
          FALLBACK
      ======================= */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
