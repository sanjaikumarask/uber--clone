// src/services/socket.ts (driver-app)

import { Storage } from "./storage";
import { WS_URL } from "./api";
import * as Notifications from "expo-notifications";
import { playNotificationSound } from "./sound";
import { useRideStore } from "../domains/rides/ride.store";

// ─────────────────────────────────────────────────────────────
// LOCATION SOCKET — driver sends GPS pings
// ─────────────────────────────────────────────────────────────
let locationSocket: WebSocket | null = null;
let locationSeq = 0;
let locationReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let locationRetryCount = 0;

export async function connectLocationSocket(): Promise<void> {
  if (locationSocket?.readyState === WebSocket.OPEN) return;

  const token = await Storage.getToken();
  if (!token) return;

  const url = `${WS_URL}/tracking/driver-location/?token=${token}`;
  console.log("[LocationSocket] Connecting:", url);

  const setStatus = useRideStore.getState().setLocationSocketStatus;
  setStatus("connecting");

  locationSocket = new WebSocket(url);

  locationSocket.onopen = () => {
    console.log("[LocationSocket] ✅ Connected");
    setStatus("connected");
    locationSeq = 0;
    locationRetryCount = 0; // Reset on success
  };

  locationSocket.onclose = (e) => {
    locationSocket = null;
    setStatus("disconnected");
    const delay = Math.min(30000, 3000 * Math.pow(2, locationRetryCount));
    console.warn(`[LocationSocket] ⚠️ Closed, retrying in ${delay}ms...`);
    locationReconnectTimer = setTimeout(() => {
      locationRetryCount++;
      connectLocationSocket();
    }, delay);
  };
}

export function disconnectLocationSocket(): void {
  if (locationReconnectTimer) clearTimeout(locationReconnectTimer);
  const setStatus = useRideStore.getState().setLocationSocketStatus;
  if (locationSocket) {
    locationSocket.onclose = () => { };
    locationSocket.close();
    locationSocket = null;
  }
  setStatus("disconnected");
}

export function sendLocation(
  lat: number,
  lng: number,
  heading: number | null,
  speedKmh?: number | null,
  accuracyM?: number | null
): void {
  if (locationSocket?.readyState === WebSocket.OPEN) {
    locationSocket.send(JSON.stringify({
      lat,
      lng,
      heading,
      speed_kmh: speedKmh ?? null,
      accuracy_m: accuracyM ?? null,
      seq: ++locationSeq,
    }));
  }
}

// ─────────────────────────────────────────────────────────────
// RIDES SOCKET — driver receives offers
// ─────────────────────────────────────────────────────────────
let ridesSocket: WebSocket | null = null;
const ridesListeners: Map<string, Array<(data: any) => void>> = new Map();
let ridesReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let ridesRetryCount = 0;

export async function connectRidesSocket(): Promise<void> {
  if (ridesSocket?.readyState === WebSocket.OPEN) return;

  const token = await Storage.getToken();
  if (!token) return;

  const url = `${WS_URL}/tracking/driver-rides/?token=${token}`;

  const setStatus = useRideStore.getState().setSocketStatus;
  setStatus("connecting");

  ridesSocket = new WebSocket(url);
  ridesSocket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const type = msg.type ?? msg.event;

      if (type === "ride_offer" || type === "ride_assigned") {
        playNotificationSound();

        const isAuto = type === "ride_assigned";
        Notifications.scheduleNotificationAsync({
          content: {
            title: isAuto ? "New Ride Assigned! ⚡" : "New Ride Offer! 🚗",
            body: isAuto
              ? "You have been auto-assigned a new ride. Head to pickup!"
              : `You have a new request for ${msg.data?.rider_name || 'a passenger'}.`,
            sound: true,
            priority: Notifications.AndroidNotificationPriority.HIGH,
          },
          trigger: null,
        });
      }

      ridesListeners.get(type)?.forEach(cb => cb(msg));
    } catch (err) { }
  };
  ridesSocket.onopen = () => {
    console.log("[RidesSocket] ✅ Connected");
    setStatus("connected");
    ridesRetryCount = 0;
  };
  ridesSocket.onclose = () => {
    ridesSocket = null;
    setStatus("disconnected");
    const delay = Math.min(30000, 3000 * Math.pow(2, ridesRetryCount));
    console.warn(`[RidesSocket] ⚠️ Closed, retrying in ${delay}ms...`);
    ridesReconnectTimer = setTimeout(() => {
      ridesRetryCount++;
      connectRidesSocket();
    }, delay);
  };
}

export function disconnectRidesSocket(): void {
  const setStatus = useRideStore.getState().setSocketStatus;
  if (ridesReconnectTimer) {
    clearTimeout(ridesReconnectTimer);
    ridesReconnectTimer = null;
  }
  if (ridesSocket) {
    ridesSocket.onclose = () => { };
    ridesSocket.close();
    ridesSocket = null;
  }
  setStatus("disconnected");
  ridesListeners.clear();
}

export function onRidesEvent(event: string, cb: (data: any) => void): () => void {
  if (!ridesListeners.has(event)) ridesListeners.set(event, []);
  ridesListeners.get(event)!.push(cb);
  return () => {
    const cbs = ridesListeners.get(event);
    if (cbs) {
      const i = cbs.indexOf(cb);
      if (i > -1) cbs.splice(i, 1);
    }
  };
}

// ─────────────────────────────────────────────────────────────
// SPECIFIC RIDE SOCKET — for chat and fine-grained updates
// ─────────────────────────────────────────────────────────────
let rideSocket: WebSocket | null = null;
const rideListeners: Map<string, Array<(data: any) => void>> = new Map();

export async function connectRideSocket(rideId: number): Promise<void> {
  if (rideSocket?.readyState === WebSocket.OPEN) return;

  const token = await Storage.getToken();
  if (!token) return;

  const url = `${WS_URL}/rides/${rideId}/?token=${token}`;
  console.log("[RideSocket] Connecting:", url);

  rideSocket = new WebSocket(url);

  rideSocket.onopen = () => console.log("[RideSocket] ✅ Connected");
  rideSocket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const eventType = msg.type || msg.event;

      if (eventType === "CHAT_MESSAGE") {
        Notifications.scheduleNotificationAsync({
          content: {
            title: `Message from Passenger 💬`,
            body: msg.message,
            sound: true,
          },
          trigger: null,
        });
      }

      rideListeners.get(eventType)?.forEach(cb => cb(msg));
    } catch (err) {
      console.error("[RideSocket] Parse error");
    }
  };
  rideSocket.onclose = () => {
    rideSocket = null;
  };
}

export function disconnectRideSocket(): void {
  if (rideSocket) {
    rideSocket.close();
    rideSocket = null;
  }
  rideListeners.clear();
}

export function onRideEvent(event: string, cb: (data: any) => void) {
  if (!rideListeners.has(event)) rideListeners.set(event, []);
  rideListeners.get(event)!.push(cb);
  return () => {
    const cbs = rideListeners.get(event);
    if (cbs) {
      const i = cbs.indexOf(cb);
      if (i > -1) cbs.splice(i, 1);
    }
  };
}

export function sendRideChat(message: string): void {
  if (rideSocket?.readyState === WebSocket.OPEN) {
    rideSocket.send(JSON.stringify({ type: "SEND_CHAT", message }));
  }
}