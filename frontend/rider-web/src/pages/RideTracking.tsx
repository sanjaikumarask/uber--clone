import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { useRideStore } from "../domains/rides/ride.store";
import { startTrackingSocket, stopTrackingSocket, sendChatMessage } from "../domains/tracking/tracking.socket";
import MapView from "../components/MapView";
import { api } from "../services/http";

const DEFAULT_CENTER = { lat: 13.0827, lng: 80.2707 };

export default function RideTracking() {
  const navigate = useNavigate();
  const {
    rideId, status, driverLocation, otpCode, eta,
    pickupAddress, dropoffAddress, messages, driver, vehicleType, trackingStatus
  } = useRideStore();

  const hasNavigated = useRef(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [msgInput, setMsgInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!rideId) return;
    startTrackingSocket(rideId);
    return () => { stopTrackingSocket(); };
  }, [rideId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatOpen]);

  useEffect(() => {
    if (status === "COMPLETED" && !hasNavigated.current) {
      hasNavigated.current = true;
      navigate(`/ride-completed/${rideId}`);
      setTimeout(() => stopTrackingSocket(), 500);
    }
    if ((status === "CANCELLED" || status === "NO_SHOW") && !hasNavigated.current) {
      hasNavigated.current = true;
      navigate("/");
      setTimeout(() => stopTrackingSocket(), 500);
    }
  }, [status, navigate, rideId]);

  const handleSend = () => {
    if (!msgInput.trim()) return;
    sendChatMessage(msgInput);
    setMsgInput("");
  };

  const triggerSOS = async () => {
    if (window.confirm("🚨 Are you in danger? This will alert emergency services.")) {
      try {
        const loc = driverLocation || { lat: 0, lng: 0 };
        await api.post(`/supports/rides/${rideId}/sos/`, { lat: loc.lat, lng: loc.lng });
        alert("Emergency alert sent. Help is on the way.");
      } catch (err) {
        alert("Failed to send SOS. Please call emergency services.");
      }
    }
  };

  const mapCenter = driverLocation ?? DEFAULT_CENTER;

  const getStatusText = () => {
    switch (status) {
      case "OFFERED": return "Waiting for driver...";
      case "ASSIGNED": return "Driver coming to you";
      case "ARRIVED": return "Driver is here — share OTP";
      case "ONGOING": return "On the way to destination";
      default: return "Connecting...";
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case "ASSIGNED": return "#276EF1";
      case "ARRIVED": return "#34C759";
      case "ONGOING": return "#FFCC00";
      default: return "#A6A6A6";
    }
  };

  return (
    <div style={styles.page}>

      {/* Top Status Bar */}
      <div style={styles.topBar}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ ...styles.statusDot, background: getStatusColor() }} />
          <span style={styles.statusText}>{getStatusText()}</span>
        </div>
        {eta && <span style={styles.etaBadge}>{eta}</span>}
        {trackingStatus !== "connected" && (
          <span style={{
            ...styles.etaBadge,
            background: "rgba(239,68,68,0.1)",
            color: "#ef4444",
            borderColor: "rgba(239,68,68,0.3)",
            marginLeft: 10
          }}>
            {trackingStatus === "connecting" ? "Connecting..." : "Offline - Reconnecting..."}
          </span>
        )}
      </div>

      {/* SOS Button */}
      <button onClick={triggerSOS} style={styles.sosBtn}>🚨 SOS</button>

      {/* Map */}
      <div style={styles.mapWrapper}>
        <MapView center={mapCenter} />
      </div>

      {/* Bottom Sheet */}
      <div style={styles.bottomSheet}>
        <div style={styles.handle} />

        {/* Driver Info */}
        <div style={styles.driverRow}>
          <div style={styles.avatar}>{driver?.first_name?.[0] ?? "D"}</div>
          <div style={{ flex: 1 }}>
            <div style={styles.driverName}>{driver?.first_name || "Your Driver"}</div>
            <div style={styles.driverMeta}>
              <span style={styles.ratingBadge}>★ {driver?.rating ?? "4.9"}</span>
              <span style={styles.vehicleBadge}>{driver?.vehicle_model || "UberGo"}</span>
            </div>
            <div style={styles.plateBadge}>{driver?.vehicle_number || "TN 01 AB 1234"}</div>
          </div>
          <img
            src={vehicleType === "moto" ? "/assets/vehicles/moto.png"
              : vehicleType === "auto" ? "/assets/vehicles/auto.png"
                : vehicleType === "xl" ? "/assets/vehicles/xl.png"
                  : "/assets/vehicles/go.png"}
            style={{ width: 64, height: 44, objectFit: "contain" }}
          />
        </div>

        <div style={styles.divider} />

        {/* OTP or Address */}
        {status === "ARRIVED" ? (
          <div style={styles.otpSection}>
            <span style={styles.otpLabel}>SHARE WITH DRIVER</span>
            <span style={styles.otpCode}>{otpCode || "----"}</span>
          </div>
        ) : (
          <div style={styles.addressSection}>
            <div style={styles.addressRow}>
              <div style={{ ...styles.dot, background: "#276EF1" }} />
              <span style={styles.addressText}>{pickupAddress || "Pickup..."}</span>
            </div>
            <div style={{ width: 1, height: 16, background: "rgba(255,255,255,0.1)", marginLeft: 3.5 }} />
            <div style={styles.addressRow}>
              <div style={{ ...styles.dot, background: "#34C759" }} />
              <span style={styles.addressText}>{dropoffAddress || "Destination..."}</span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={styles.actionRow}>
          <button onClick={() => setChatOpen(true)} style={styles.actionBtn}>
            💬 Message
          </button>
          <button onClick={triggerSOS} style={{ ...styles.actionBtn, color: "#FF3B30" }}>
            🛡 Safety
          </button>
          <button onClick={async () => {
            if (window.confirm("Cancel this ride?")) {
              await useRideStore.getState().cancelRide(rideId!);
            }
          }} style={{ ...styles.actionBtn, color: "#A6A6A6" }}>
            ✕ Cancel
          </button>
        </div>
      </div>

      {/* Chat Overlay */}
      {chatOpen && (
        <div style={styles.chatOverlay}>
          <div style={styles.chatHeader}>
            <span style={{ fontWeight: 700, color: "#fff" }}>
              Chat with {driver?.first_name || "Driver"}
            </span>
            <button onClick={() => setChatOpen(false)} style={{ color: "#A6A6A6", fontSize: 20, background: "none", border: "none", cursor: "pointer" }}>✕</button>
          </div>
          <div style={styles.messageList}>
            {messages.map((m: any, i: number) => (
              <div key={i} style={m.sender_id === 0 ? styles.myMsg : styles.theirMsg}>
                {m.message}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
          <div style={styles.chatInputRow}>
            <input
              value={msgInput}
              onChange={e => setMsgInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSend()}
              placeholder="Send a message..."
              style={styles.chatInput}
            />
            <button onClick={handleSend} style={styles.sendBtn}>Send</button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
      `}</style>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "flex", flexDirection: "column", height: "100vh",
    position: "relative", backgroundColor: "#000", overflow: "hidden",
    fontFamily: "'Outfit', sans-serif"
  },
  topBar: {
    position: "absolute", top: 20, left: 16, right: 16, zIndex: 100,
    backgroundColor: "rgba(10,12,18,0.7)", backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    borderRadius: "20px", padding: "16px 22px",
    border: "1px solid rgba(255,255,255,0.08)",
    display: "flex", justifyContent: "space-between", alignItems: "center",
    boxShadow: "0 12px 40px rgba(0,0,0,0.7)",
  },
  statusDot: {
    width: 6, height: 6, borderRadius: "50%",
    animation: "pulse 2s infinite",
  },
  statusText: { color: "#f1f5f9", fontSize: "14px", fontWeight: 700, letterSpacing: "-0.2px" },
  etaBadge: {
    backgroundColor: "rgba(39,110,241,0.1)", color: "#276EF1",
    padding: "6px 14px", borderRadius: "12px", fontSize: "12px", fontWeight: 800,
    border: "1px solid rgba(39,110,241,0.25)",
    boxShadow: "0 4px 12px rgba(39,110,241,0.15)",
  },
  sosBtn: {
    position: "absolute", top: 100, right: 16, zIndex: 100,
    backgroundColor: "rgba(255,59,48,0.9)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "14px", padding: "8px 16px", fontSize: "11px",
    fontWeight: 900, cursor: "pointer", letterSpacing: "0.1em",
    boxShadow: "0 8px 24px rgba(255,59,48,0.4)", backdropFilter: "blur(8px)",
  },
  mapWrapper: { flex: 1 },
  bottomSheet: {
    position: "absolute", bottom: 20, left: 20, right: 20, zIndex: 200,
    background: "rgba(10,12,18,0.75)", backdropFilter: "blur(40px)",
    WebkitBackdropFilter: "blur(40px)",
    borderRadius: "28px",
    padding: "16px 24px 32px",
    border: "1px solid rgba(255,255,255,0.1)",
    boxShadow: "0 -20px 80px rgba(0,0,0,0.8)",
    animation: "slideUp 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
    maxWidth: "500px", margin: "0 auto",
  },
  handle: {
    width: 44, height: 4, backgroundColor: "rgba(255,255,255,0.12)",
    borderRadius: 10, margin: "0 auto 20px",
  },
  driverRow: { display: "flex", alignItems: "center", gap: 18, marginBottom: 20 },
  avatar: {
    width: 56, height: 56, borderRadius: "18px",
    backgroundColor: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
    display: "flex", justifyContent: "center", alignItems: "center",
    fontSize: 24, fontWeight: 800, color: "#fff",
    boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
  },
  driverName: { fontSize: 18, fontWeight: 800, color: "#fff", letterSpacing: "-0.4px" },
  driverMeta: { display: "flex", gap: 10, marginTop: 4, alignItems: "center" },
  ratingBadge: { fontSize: 13, color: "#FFB000", fontWeight: 800, display: "flex", alignItems: "center", gap: 4 },
  vehicleBadge: { fontSize: 13, color: "#94a3b8", fontWeight: 500 },
  plateBadge: {
    marginTop: 6, display: "inline-block",
    backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "8px",
    padding: "4px 10px", fontSize: 11, fontWeight: 800,
    color: "#cbd5e1", letterSpacing: "0.12em", border: "1px solid rgba(255,255,255,0.07)",
  },
  divider: { height: 1, backgroundColor: "rgba(255,255,255,0.06)", margin: "20px 0" },
  otpSection: { textAlign: "center", padding: "12px 0", background: "rgba(52,199,89,0.03)", borderRadius: "20px", border: "1px solid rgba(52,199,89,0.1)" },
  otpLabel: { fontSize: 9, fontWeight: 900, color: "#34C759", display: "block", letterSpacing: "0.2em", marginBottom: 8, opacity: 0.8 },
  otpCode: { fontSize: 38, fontWeight: 900, letterSpacing: 14, color: "#34C759", textShadow: "0 0 20px rgba(52,199,89,0.3)" },
  addressSection: { display: "flex", flexDirection: "column", gap: 4 },
  addressRow: { display: "flex", alignItems: "center", gap: 14, padding: "2px 0" },
  dot: { width: 8, height: 8, borderRadius: "50%", flexShrink: 0, border: "2px solid rgba(0,0,0,0.5)" },
  addressText: { fontSize: 14, color: "#94a3b8", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  actionRow: {
    display: "flex", gap: 12, marginTop: 24,
  },
  actionBtn: {
    flex: 1, padding: "14px 0", borderRadius: "16px",
    backgroundColor: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    color: "#f8fafc", fontWeight: 800, fontSize: 12, cursor: "pointer",
    transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
    textTransform: "uppercase", letterSpacing: "0.5px"
  },
  chatOverlay: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000,
    background: "rgba(5,7,12,0.95)", backdropFilter: "blur(40px)",
    display: "flex", flexDirection: "column", animation: "slideUp 0.4s ease-out",
  },
  chatHeader: {
    padding: "20px 20px 16px",
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  messageList: {
    flex: 1, padding: "16px 20px", overflowY: "auto",
    display: "flex", flexDirection: "column", gap: 10,
  },
  myMsg: {
    alignSelf: "flex-end",
    backgroundColor: "#276EF1", color: "#fff",
    padding: "10px 16px", borderRadius: "18px 18px 2px 18px",
    maxWidth: "80%", fontSize: 13,
  },
  theirMsg: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(255,255,255,0.08)", color: "#fff",
    padding: "10px 16px", borderRadius: "18px 18px 18px 2px",
    maxWidth: "80%", fontSize: 13,
    border: "1px solid rgba(255,255,255,0.08)",
  },
  chatInputRow: {
    padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,0.08)",
    display: "flex", gap: 10,
  },
  chatInput: {
    flex: 1, padding: "12px 16px", borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.1)",
    color: "#fff", fontSize: 14, outline: "none",
  },
  sendBtn: {
    padding: "12px 20px", borderRadius: 12,
    backgroundColor: "#276EF1", color: "#fff",
    border: "none", fontWeight: 700, cursor: "pointer",
  },
};