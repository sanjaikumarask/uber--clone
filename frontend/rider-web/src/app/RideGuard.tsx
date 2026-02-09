import { Navigate } from "react-router-dom";
import { useRideStore } from "../store/ride.store";
import { ReactNode } from "react";

type RideStatus = "SEARCHING" | "ASSIGNED" | "ARRIVED" | "ONGOING";

export default function RideGuard({
  allow,
  children,
}: {
  allow: RideStatus[];
  children: ReactNode;
}) {
  const status = useRideStore((s) => s.status);

  // No active ride → kick out
  if (!status) {
    return <Navigate to="/home" replace />;
  }

  // Wrong page for this state → redirect correctly
  if (!allow.includes(status)) {
    if (status === "SEARCHING") {
      return <Navigate to="/ride/searching" replace />;
    }

    return <Navigate to="/ride/tracking" replace />;
  }

  return <>{children}</>;
}
