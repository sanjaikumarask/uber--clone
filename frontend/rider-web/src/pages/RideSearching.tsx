import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useRideStore } from "../store/ride.store";
import { cancelRide } from "../services/ride.service";

export default function RideSearching() {
  const navigate = useNavigate();
  const rideId = useRideStore((s) => s.rideId);
  const status = useRideStore((s) => s.status);
  const clear = useRideStore((s) => s.clear);

  useEffect(() => {
    if (!status) return;

    if (
      status === "ASSIGNED" ||
      status === "ARRIVED" ||
      status === "ONGOING"
    ) {
      navigate("/ride/tracking", { replace: true });
    }

    if (status === "CANCELLED") {
      clear();
      navigate("/home", { replace: true });
    }
  }, [status, navigate, clear]);

  const onCancel = async () => {
    if (!rideId) return;
    await cancelRide(rideId);
  };

  return (
    <div>
      <h2>Finding Driver…</h2>
      <p>Status: {status}</p>
      <button onClick={onCancel}>Cancel Ride</button>
    </div>
  );
}
