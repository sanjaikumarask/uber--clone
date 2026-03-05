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
      minHeight: "100vh", backgroundColor: "#020408", padding: "32px 20px",
      fontFamily: "'Outfit', sans-serif",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Background Decorative Glows */}
      <div style={{ position: "absolute", top: "-10%", left: "-10%", width: "40vw", height: "40vw", background: "radial-gradient(circle, rgba(39,110,241,0.05) 0%, transparent 70%)", zIndex: 0 }} />
      <div style={{ position: "absolute", bottom: "-10%", right: "-10%", width: "50vw", height: "50vw", background: "radial-gradient(circle, rgba(6,182,212,0.03) 0%, transparent 70%)", zIndex: 0 }} />

      <div style={{ width: "100%", maxWidth: "440px", textAlign: "center", zIndex: 1 }}>

        {/* Vehicle Animation Container */}
        <div style={{ position: "relative", width: "180px", height: "120px", margin: "0 auto 64px", display: "flex", alignItems: "center", justifyContent: "center" }}>

          {/* Multi-layered Radar Pulses */}
          {[...Array(4)].map((_, i) => (
            <div key={i} style={{
              position: "absolute", top: "50%", left: "50%",
              width: "200px", height: "200px",
              marginLeft: "-100px", marginTop: "-100px",
              borderRadius: "50%",
              border: `1.5px solid rgba(39,110,241,${0.4 - i * 0.1})`,
              boxShadow: i === 0 ? "0 0 30px rgba(39,110,241,0.2)" : "none",
              animation: `radar 3s infinite ${i * 0.7}s cubic-bezier(0.4, 0, 0.2, 1)`,
            }} />
          ))}

          <img
            src={vehicleType === "moto" ? "/assets/vehicles/moto.png"
              : vehicleType === "auto" ? "/assets/vehicles/auto.png"
                : vehicleType === "xl" ? "/assets/vehicles/xl.png"
                  : "/assets/vehicles/go.png"}
            style={{
              width: "120px", height: "80px", objectFit: "contain",
              zIndex: 2, filter: "drop-shadow(0 12px 24px rgba(0,0,0,0.5))",
              animation: "float 4s ease-in-out infinite"
            }}
          />
        </div>

        <h1 style={{ fontSize: "2rem", fontWeight: 800, color: "#f8fafc", marginBottom: 12, letterSpacing: "-0.5px" }}>
          Finding Your Ride
        </h1>
        <p style={{ fontSize: "1rem", color: "#94a3b8", marginBottom: 48, fontWeight: 500 }}>
          {status === "OFFERED" ? "Securing your driver..." : "Optimizing for nearby drivers..."}
        </p>

        {/* Info Card / Glass Panel */}
        <div style={{
          background: "rgba(15,23,42,0.4)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 28, padding: "28px 32px",
          marginBottom: 32, textAlign: "left",
          boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
        }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontSize: 10, fontWeight: 900, color: "#64748b", letterSpacing: "1.5px", textTransform: "uppercase" }}>Request ID</span>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#f1f5f9", marginTop: 4 }}># {rideId}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: 10, fontWeight: 900, color: "#64748b", letterSpacing: "1.5px", textTransform: "uppercase" }}>Status</span>
                <div style={{
                  fontSize: 14, fontWeight: 800, color: "#276EF1", marginTop: 4,
                  display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end"
                }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#276EF1", animation: "pulse 1.5s infinite" }} />
                  {status === "OFFERED" ? "CONFIRMING" : "SCANNING"}
                </div>
              </div>
            </div>

            <div style={{ height: 1, backgroundColor: "rgba(255,255,255,0.06)" }} />

            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, backgroundColor: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                {vehicleType === "moto" ? "🏍" : vehicleType === "auto" ? "🛺" : "🚗"}
              </div>
              <div>
                <span style={{ fontSize: 10, fontWeight: 900, color: "#64748b", letterSpacing: "1.5px", textTransform: "uppercase" }}>Vehicle Class</span>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#f1f5f9", marginTop: 2, textTransform: "capitalize" }}>Metropolis {vehicleType}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleCancel}
          style={{
            width: "100%", padding: "18px",
            backgroundColor: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 20, color: "#94a3b8",
            fontWeight: 800, fontSize: "12px", cursor: "pointer",
            textTransform: "uppercase", letterSpacing: "1px",
            transition: "all 0.3s ease",
          }}
          onMouseEnter={e => { e.currentTarget.style.backgroundColor = "rgba(239,68,68,0.08)"; e.currentTarget.style.color = "#ef4444"; e.currentTarget.style.borderColor = "rgba(239,68,68,0.2)"; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.03)"; e.currentTarget.style.color = "#94a3b8"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; }}
        >
          Cancel Request
        </button>

        {/* GPS Insight */}
        <div style={{
          marginTop: 32, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          opacity: 0.6
        }}>
          <div style={{ width: 4, height: 4, borderRadius: "50%", background: gpsStatus === "sharing" ? "#34C759" : "#f59e0b" }} />
          <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: "0.5px" }}>
            {gpsStatus === "sharing" ? "TELEMETRY SYNCHRONIZED" : "INITIALIZING SIGNAL..."}
          </span>
        </div>
      </div>

      <style>{`
        @keyframes radar {
          0%   { transform: scale(0.5); opacity: 1; }
          100% { transform: scale(2.5); opacity: 0; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0) scale(1.1); }
          50% { transform: translateY(-10px) scale(1.1); }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.2); opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
  

