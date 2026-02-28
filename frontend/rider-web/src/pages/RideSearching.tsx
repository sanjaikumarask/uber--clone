import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRideStore } from "../domains/rides/ride.store";
import { startTrackingSocket, sendRiderLocation } from "../domains/tracking/tracking.socket";

export default function RideSearching() {
  const navigate = useNavigate();
  const { rideId, status, cancelRide, pickup, vehicleType } = useRideStore();
  const [gpsStatus, setGpsStatus] = useState<"locating" | "sharing" | "denied">("locating");

  const handleCancel = async () => {
    if (rideId) {
      try {
        await cancelRide(rideId);
      } catch (err) {
        console.error("Failed to cancel from searching page:", err);
      }
    }
    navigate("/");
  };

  useEffect(() => {
    if (!rideId) {
      navigate("/");
      return;
    }
    startTrackingSocket(rideId);
  }, [rideId, navigate]);

  useEffect(() => {
    if (status && ["ASSIGNED", "ARRIVED", "ONGOING"].includes(status)) {
      navigate("/ride/tracking");
    }
    if (status === "CANCELLED" || status === "NO_SHOW") {
      navigate("/");
    }
    if (status === "COMPLETED") {
      navigate(`/ride-completed/${rideId}`);
    }
  }, [status, navigate, rideId]);

  useEffect(() => {
    if (!rideId) return;

    if (pickup) {
      sendRiderLocation(pickup.lat, pickup.lng);
      setGpsStatus("sharing");
    }

    if (!navigator.geolocation) {
      setGpsStatus("denied");
      return;
    }

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const sendGps = (pos: GeolocationPosition) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      sendRiderLocation(lat, lng);
      setGpsStatus("sharing");
    };

    navigator.geolocation.getCurrentPosition(sendGps, () => {
      setGpsStatus(pickup ? "sharing" : "denied");
    }, { enableHighAccuracy: true, timeout: 8000 });

    intervalId = setInterval(() => {
      navigator.geolocation.getCurrentPosition(sendGps, () => { }, { enableHighAccuracy: true });
    }, 30000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [rideId]);

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      minHeight: "100vh", backgroundColor: "#0A0A0A", padding: "32px 20px",
    }}>
      <div style={{ width: "100%", maxWidth: "400px", textAlign: "center" }}>

        {/* Vehicle Animation */}
        <div style={{ position: "relative", width: "160px", height: "100px", margin: "0 auto 48px" }}>
          <img
            src={vehicleType === "moto" ? "/assets/vehicles/moto.png"
              : vehicleType === "auto" ? "/assets/vehicles/auto.png"
                : vehicleType === "xl" ? "/assets/vehicles/xl.png"
                  : "/assets/vehicles/go.png"}
            style={{ width: "100%", height: "100%", objectFit: "contain", transform: "scale(1.2)" }}
          />
          {/* Radar Ring 1 */}
          <div style={{
            position: "absolute", top: "50%", left: "50%",
            width: "180px", height: "180px",
            marginLeft: "-90px", marginTop: "-90px",
            borderRadius: "50%", border: "1.5px solid rgba(39,110,241,0.4)",
            animation: "radar 2s infinite",
          }} />
          {/* Radar Ring 2 */}
          <div style={{
            position: "absolute", top: "50%", left: "50%",
            width: "240px", height: "240px",
            marginLeft: "-120px", marginTop: "-120px",
            borderRadius: "50%", border: "1px solid rgba(39,110,241,0.2)",
            animation: "radar 2s infinite 0.6s",
          }} />
        </div>

        <h1 style={{ fontSize: "1.75rem", fontWeight: 800, color: "#fff", marginBottom: 8 }}>
          Finding your ride
        </h1>
        <p style={{ fontSize: "0.95rem", color: "#A6A6A6", marginBottom: 40 }}>
          Matching you with a nearby driver...
        </p>

        {/* Info Card */}
        <div style={{
          backgroundColor: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 16, padding: "20px 24px",
          marginBottom: 24, textAlign: "left",
          backdropFilter: "blur(10px)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#666", letterSpacing: "0.1em" }}>REQUEST ID</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#fff" }}>#{rideId}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#666", letterSpacing: "0.1em" }}>STATUS</span>
            <span style={{ fontSize: 12, fontWeight: 900, color: "#276EF1" }}>
              {status === "OFFERED" ? "CONFIRMING..." : "SEARCHING..."}
            </span>
          </div>
        </div>

        {/* Cancel Button */}
        <button
          onClick={handleCancel}
          style={{
            width: "100%", padding: "16px",
            backgroundColor: "rgba(255,255,255,0.07)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 12, color: "#fff",
            fontWeight: 700, fontSize: "0.95rem", cursor: "pointer",
          }}
        >
          Cancel Request
        </button>

        {/* GPS Status */}
        <p style={{ marginTop: 20, fontSize: 11, color: "#555" }}>
          {gpsStatus === "sharing" ? "📍 Location shared for accuracy" : "⌛ Acquiring precise location..."}
        </p>
      </div>

      <style>{`
        @keyframes radar {
          0%   { transform: scale(0.5); opacity: 0.8; }
          100% { transform: scale(1.5); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
