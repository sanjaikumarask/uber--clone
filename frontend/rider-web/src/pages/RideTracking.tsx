import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useRideStore } from "../store/ride.store";
import MapView from "../components/MapView";

export default function RideTracking() {
  const navigate = useNavigate();
  const status = useRideStore((s) => s.status);
  const clear = useRideStore((s) => s.clear);

  useEffect(() => {
    if (status === "COMPLETED" || status === "CANCELLED") {
      clear();
      navigate("/home", { replace: true });
    }
  }, [status, clear, navigate]);

  const pickup = { lat: 12.9716, lng: 77.5946 };

  return (
    <>
      <h2>Ride Status: {status}</h2>
      <MapView center={pickup} />
    </>
  );
}
