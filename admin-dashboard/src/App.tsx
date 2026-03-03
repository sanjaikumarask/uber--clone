import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/Layout.tsx";
import Overview from "./pages/Overview.tsx";
import Drivers from "./pages/Drivers.tsx";
import LiveMap from "./pages/LiveMap.tsx";
import AdminRides from "./pages/AdminRides.tsx";
import Login from "./pages/Login.tsx";
import Offers from "./pages/Offers.tsx";
import Ledger from "./pages/Ledger.tsx";
import Payouts from "./pages/Payouts.tsx";
import DriverIncentives from "./pages/DriverIncentives.tsx";
import Analytics from "./pages/Analytics.tsx";
import Verification from "./pages/Verification.tsx";
import Support from "./pages/Support.tsx";
import Reports from "./pages/Reports.tsx";
import FareConfig from "./pages/FareConfig.tsx";
import Payments from "./pages/Payments.tsx";
import Alerts from "./pages/Alerts.tsx";
import Observability from "./pages/Observability.tsx";

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
          <Route path="/ledger" element={<Ledger />} />
          <Route path="/payouts" element={<Payouts />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/offers" element={<Offers />} />
          <Route path="/incentives" element={<DriverIncentives />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/verification" element={<Verification />} />
          <Route path="/support" element={<Support />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/fare-config" element={<FareConfig />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/live-map" element={<LiveMap />} />
          <Route path="/observability" element={<Observability />} />
        </Route>

        {/* FALLBACK */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
