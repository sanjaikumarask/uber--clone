import { useNavigate } from "react-router-dom";
import { useRideStore } from "../domains/rides/ride.store";
import MapView from "../components/MapView";

export default function BookRide() {
  const navigate = useNavigate();
  const createRide = useRideStore((s) => s.createRide);
  const checkActiveRide = useRideStore((s) => s.checkActiveRide);

  const requestRide = async () => {
    try {
      const active = await checkActiveRide();

      if (active.ride_id) {
        navigate("/ride/searching");
        return;
      }

      await createRide({
        pickup_lat: 12.9716,
        pickup_lng: 77.5946,
        drop_lat: 12.9352,
        drop_lng: 77.6245,
      });

      navigate("/ride/searching");
    } catch (err: any) {
      if (err.message === "ACTIVE_RIDE_EXISTS") {
        navigate("/ride/searching");
        return;
      }

      alert("Failed to request ride");
    }
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1, minHeight: "400px" }}>
        <MapView center={{ lat: 12.9716, lng: 77.5946 }} />
      </div>

      <div className="card" style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        borderRadius: "var(--radius-lg) var(--radius-lg) 0 0",
        zIndex: 10
      }}>
        <h2 className="text-h2" style={{ marginBottom: "var(--spacing-md)" }}>
          Confirm Your Ride
        </h2>

        <div style={{ display: "flex", gap: "var(--spacing-sm)", marginBottom: "var(--spacing-lg)" }}>
          <div>From: <strong>MG Road</strong></div>
          <div>To: <strong>Koramangala</strong></div>
        </div>

        <button
          onClick={requestRide}
          className="btn btn-primary"
        >
          Confirm Request
        </button>
      </div>
    </div>
  );
}
