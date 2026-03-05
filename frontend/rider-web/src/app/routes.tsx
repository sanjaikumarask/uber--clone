import { Routes, Route, Navigate } from "react-router-dom";
import RequireAuth from "./RequireAuth";
import RequireAdmin from "./RequireAdmin";
import Layout from "../components/Layout";
import Login from "../pages/Login";
import Signup from "../pages/Signup";
import Home from "../pages/Home";
import BookRide from "../pages/BookRide";
import Searching from "../pages/RideSearching";
import Tracking from "../pages/RideTracking";
import Completed from "../pages/RideCompleted";
import OffersPage from "../pages/OffersPage";
import AdminDashboard from "../pages/AdminDashboard";
import SupportPage from "../pages/SupportPage";
import CreateTicketPage from "../pages/CreateTicketPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<Home />} />
          <Route path="/book" element={<BookRide />} />
          <Route path="/ride/searching" element={<Searching />} />
          <Route path="/ride/tracking" element={<Tracking />} />
          <Route path="/ride-completed/:rideId" element={<Completed />} />
          <Route path="/offers" element={<OffersPage />} />
          <Route element={<RequireAdmin />}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
          </Route>
          <Route path="/support" element={<SupportPage />} />
          <Route path="/support/create" element={<CreateTicketPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  );
}
