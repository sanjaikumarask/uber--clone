import { Routes, Route, Navigate } from "react-router-dom";
import RequireAuth from "./RequireAuth";
import Layout from "../components/Layout";

import Login from "../pages/Login";
import Home from "../pages/Home";
import BookRide from "../pages/BookRide";
import Searching from "../pages/RideSearching";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<Home />} />
          <Route path="/book" element={<BookRide />} />
          <Route path="/ride/searching" element={<Searching />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  );
}
