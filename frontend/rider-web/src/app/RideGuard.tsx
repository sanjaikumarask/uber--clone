import { Navigate, Outlet } from "react-router-dom";
import { useRideStore } from "../domains/rides/ride.store";

interface Props {
  allow: string[];
}

export default function RideGuard({ allow }: Props) {
  const status = useRideStore((s) => s.status);

  if (!status || !allow.includes(status)) {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
}
