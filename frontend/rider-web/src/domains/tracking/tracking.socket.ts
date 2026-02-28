// src/domains/tracking/tracking.socket.ts

import { useRideStore } from "../rides/ride.store";
import { soundService } from "../../services/sound";

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let currentRideId: number | null = null;
let rideCompletedFired = false; // guard: only process RIDE_COMPLETED once

export function startTrackingSocket(rideId: number) {
  if (!rideId) return;
  currentRideId = rideId;
  rideCompletedFired = false; // reset for new connection

  if (socket && socket.readyState === WebSocket.OPEN) return;

  const token = localStorage.getItem("access");
  if (!token) {
    console.error("[TrackingSocket] No access token");
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${protocol}://${window.location.host}/ws/rides/${rideId}/?token=${token}`;

  console.log("🔌 Connecting WS:", wsUrl);
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("✅ WS connected");
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log("📡 WS event:", msg.type, msg);

      switch (msg.type) {
        case "WS_CONNECTED": {
          const ride = msg.payload?.ride;
          if (ride?.status) {
            useRideStore.getState().setStatus(ride.status);
          }
          if (ride?.otp_code) {
            useRideStore.getState().setOtpCode(ride.otp_code);
          }
          const poly = ride?.polyline || ride?.planned_route_polyline;
          if (poly) {
            useRideStore.getState().setPolyline(poly);
          }
          if (ride?.vehicle_type) {
            useRideStore.getState().setVehicleType(ride.vehicle_type);
          }
          const driver = ride?.driver;
          if (driver?.lat != null && driver?.lng != null) {
            useRideStore.getState().setDriverLocation(driver.lat, driver.lng);
          }
          break;
        }

        case "RIDE_OFFERED": {
          useRideStore.getState().setStatus("OFFERED");
          soundService.play();
          break;
        }
        case "DRIVER_LOCATION_UPDATED": {
          const { lat, lng, eta, heading } = msg.payload ?? {};
          if (lat != null && lng != null) {
            useRideStore.getState().setDriverLocation(lat, lng);
          }
          if (heading != null) {
            useRideStore.getState().setHeading(heading);
          }
          if (eta != null) {
            useRideStore.getState().setEta(`${eta} min`);
          }
          break;
        }

        case "RIDE_COMPLETED": {
          // Guard: only process the FIRST RIDE_COMPLETED per socket session.
          if (rideCompletedFired) break;
          rideCompletedFired = true;
          // Set fare FIRST so the RideCompleted payment page has the amount
          const fare = msg.payload?.fare ?? msg.fare ?? null;
          if (fare != null) {
            useRideStore.getState().setFare(fare);
          }
          // Status change triggers navigation in RideTracking's useEffect.
          // The tracking page will call stopTrackingSocket() after navigating.
          useRideStore.getState().setStatus("COMPLETED");
          break;
        }

        case "RIDE_STATUS_UPDATED": {
          const payload = msg.payload ?? {};
          if (payload.vehicle_type) {
            useRideStore.getState().setVehicleType(payload.vehicle_type);
          }
          const status = payload.status ?? msg.status;
          // COMPLETED is handled exclusively by RIDE_COMPLETED (which carries fare).
          // Ignoring it here prevents navigating to the payment page before fare is set.
          if (status === "COMPLETED") break;
          if (status) {
            useRideStore.getState().setStatus(status);
            if (status !== "SEARCHING") soundService.play();
          }
          if (payload.otp_code) {
            useRideStore.getState().setOtpCode(payload.otp_code);
          }
          if (payload.final_fare) {
            useRideStore.getState().setFare(payload.final_fare);
          }
          const poly = payload.polyline || payload.planned_route_polyline;
          if (poly) {
            useRideStore.getState().setPolyline(poly);
          }
          const driver = payload.driver;
          if (driver?.lat != null && driver?.lng != null) {
            useRideStore.getState().setDriverLocation(driver.lat, driver.lng);
          }
          break;
        }

        case "NEW_CHAT_MESSAGE": {
          const payload = msg.payload ?? {};
          if (payload.message) {
            useRideStore.getState().addMessage({
              sender_id: payload.sender_id,
              message: payload.message,
              created_at: payload.created_at
            });
          }
          break;
        }

        default:
          break;
      }

    } catch (err) {
      console.error("[TrackingSocket] Failed to parse message:", err);
    }
  };

  socket.onerror = (err) => {
    console.error("[TrackingSocket] ❌ Error:", err);
  };

  socket.onclose = async (e) => {
    console.warn("[TrackingSocket] ⚠️ Closed. Code:", e.code);
    socket = null;

    // If it's a normal closure or an eviction, don't reconnect
    if (e.code === 1000 || e.code === 4001) return;

    // Check store status
    const store = useRideStore.getState();
    const status = store.status;

    if (
      currentRideId &&
      status !== "COMPLETED" &&
      status !== "CANCELLED" &&
      status !== "NO_SHOW"
    ) {
      // Before reconnecting, verify with API if the ride is still active
      // This prevents infinite reconnect loops for cancelled/invalid rides
      try {
        const active = await store.checkActiveRide();
        if (!active || active.ride_id !== currentRideId) {
          console.log("[TrackingSocket] Ride no longer active, stopping reconnection.");
          return;
        }

        console.log("[TrackingSocket] Reconnecting in 3s...");
        reconnectTimer = setTimeout(() => {
          if (currentRideId) startTrackingSocket(currentRideId);
        }, 3000);
      } catch (err) {
        console.error("[TrackingSocket] Failed to verify ride status:", err);
      }
    }
  };
}

export function stopTrackingSocket() {
  currentRideId = null;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close(1000, "ride done");
    socket = null;
  }
}

export function sendChatMessage(message: string) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: "SEND_CHAT",
      message: message
    }));
  } else {
    console.warn("[TrackingSocket] Cannot send message: WS not open");
  }
}

export function sendRiderLocation(lat: number, lng: number) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: "LOCATION_UPDATE",
      payload: { lat, lng }
    }));
  }
}