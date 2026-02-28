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
    pickupAddress, dropoffAddress, messages, driver, vehicleType
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
  },
  topBar: {
    position: "absolute", top: 20, left: 16, right: 16, zIndex: 100,
    backgroundColor: "rgba(10,10,10,0.9)", backdropFilter: "blur(20px)",
    borderRadius: "14px", padding: "14px 18px",
    border: "1px solid rgba(255,255,255,0.08)",
    display: "flex", justifyContent: "space-between", alignItems: "center",
    boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
  },
  statusDot: {
    width: 8, height: 8, borderRadius: "50%",
    animation: "pulse 2s infinite",
  },
  statusText: { color: "#fff", fontSize: "14px", fontWeight: 600 },
  etaBadge: {
    backgroundColor: "rgba(39,110,241,0.15)", color: "#276EF1",
    padding: "4px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: 700,
    border: "1px solid rgba(39,110,241,0.3)",
  },
  sosBtn: {
    position: "absolute", top: 90, right: 16, zIndex: 100,
    backgroundColor: "#FF3B30", color: "#fff", border: "none",
    borderRadius: "20px", padding: "6px 14px", fontSize: "11px",
    fontWeight: 800, cursor: "pointer", letterSpacing: "0.05em",
    boxShadow: "0 4px 16px rgba(255,59,48,0.5)",
  },
  mapWrapper: { flex: 1 },
  bottomSheet: {
    position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 200,
    background: "rgba(10,10,10,0.97)", backdropFilter: "blur(30px)",
    WebkitBackdropFilter: "blur(30px)",
    borderTopLeftRadius: "24px", borderTopRightRadius: "24px",
    padding: "12px 20px 36px",
    border: "1px solid rgba(255,255,255,0.08)",
    boxShadow: "0 -10px 50px rgba(0,0,0,0.9)",
    animation: "slideUp 0.4s ease-out",
  },
  handle: {
    width: 40, height: 4, backgroundColor: "rgba(255,255,255,0.15)",
    borderRadius: 10, margin: "0 auto 18px",
  },
  driverRow: { display: "flex", alignItems: "center", gap: 14, marginBottom: 16 },
  avatar: {
    width: 48, height: 48, borderRadius: "50%",
    backgroundColor: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)",
    display: "flex", justifyContent: "center", alignItems: "center",
    fontSize: 20, fontWeight: 800, color: "#fff",
  },
  driverName: { fontSize: 16, fontWeight: 700, color: "#fff" },
  driverMeta: { display: "flex", gap: 8, marginTop: 2 },
  ratingBadge: { fontSize: 12, color: "#FFCC00", fontWeight: 700 },
  vehicleBadge: { fontSize: 12, color: "#A6A6A6" },
  plateBadge: {
    marginTop: 4, display: "inline-block",
    backgroundColor: "rgba(255,255,255,0.08)", borderRadius: 4,
    padding: "2px 8px", fontSize: 11, fontWeight: 700,
    color: "#A6A6A6", letterSpacing: "0.08em",
  },
  divider: { height: 1, backgroundColor: "rgba(255,255,255,0.07)", margin: "14px 0" },
  otpSection: { textAlign: "center", padding: "8px 0" },
  otpLabel: { fontSize: 10, fontWeight: 700, color: "#A6A6A6", display: "block", letterSpacing: "0.1em", marginBottom: 6 },
  otpCode: { fontSize: 36, fontWeight: 900, letterSpacing: 10, color: "#34C759" },
  addressSection: { display: "flex", flexDirection: "column" },
  addressRow: { display: "flex", alignItems: "center", gap: 12, padding: "4px 0" },
  dot: { width: 7, height: 7, borderRadius: "50%", flexShrink: 0 },
  addressText: { fontSize: 13, color: "#A6A6A6", fontWeight: 500 },
  actionRow: {
    display: "flex", gap: 10, marginTop: 18,
    borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 16,
  },
  actionBtn: {
    flex: 1, padding: "12px 0", borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)",
    color: "#fff", fontWeight: 700, fontSize: 12, cursor: "pointer",
  },
  chatOverlay: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000,
    background: "rgba(5,5,5,0.98)", backdropFilter: "blur(30px)",
    display: "flex", flexDirection: "column",
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