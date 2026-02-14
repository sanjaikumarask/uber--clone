import { useEffect } from "react";
import { useRideStore } from "../domains/rides/ride.store";
import { startTrackingSocket } from "../domains/tracking/tracking.socket";
import MapView from "../components/MapView";

export default function RideSearching() {
  const rideId = useRideStore((s) => s.rideId);
  const status = useRideStore((s) => s.status);
  const driverLocation = useRideStore((s) => s.driverLocation);

  useEffect(() => {
    if (rideId) startTrackingSocket(rideId);
  }, [rideId]);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1 }}>
        <MapView
          center={driverLocation ?? { lat: 12.9716, lng: 77.5946 }}
        />
      </div>

      <div className="card text-center" style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        borderRadius: "var(--radius-lg) var(--radius-lg) 0 0",
        paddingBottom: "var(--spacing-xl)",
        zIndex: 10
      }}>
        <h2 className="text-h2" style={{ marginBottom: "var(--spacing-sm)" }}>
          {status === "SEARCHING" ? "Finding you a driver..." : `Status: ${status}`}
        </h2>
        {status === "SEARCHING" && (
          <div style={{ color: "var(--color-accent)", margin: "var(--spacing-md) 0" }}>
            <i className="loader-spinner" /> {/* Add spinner css later if needed */}
            Please wait...
          </div>
        )}

        <p className="text-sm">Ride ID: #{rideId}</p>
      </div>
    </div>
  );
}
