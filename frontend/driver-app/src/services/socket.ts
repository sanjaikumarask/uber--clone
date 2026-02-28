// src/services/socket.ts (driver-app)

import { Storage } from "./storage";
import { WS_URL } from "./api";
import * as Notifications from "expo-notifications";
import { playNotificationSound } from "./sound";

// ─────────────────────────────────────────────────────────────
// LOCATION SOCKET — driver sends GPS pings
// ─────────────────────────────────────────────────────────────
let locationSocket: WebSocket | null = null;
let locationSeq = 0;
let locationReconnectTimer: ReturnType<typeof setTimeout> | null = null;

export async function connectLocationSocket(): Promise<void> {
  if (locationSocket?.readyState === WebSocket.OPEN) return;

  const token = await Storage.getToken();
  if (!token) return;

  const url = `${WS_URL}/tracking/driver-location/?token=${token}`;
  console.log("[LocationSocket] Connecting:", url);

  locationSocket = new WebSocket(url);

  locationSocket.onopen = () => {
    console.log("[LocationSocket] ✅ Connected");
    locationSeq = 0;
  };

  locationSocket.onclose = (e) => {
    console.warn("[LocationSocket] ⚠️ Closed, reconnecting...");
    locationSocket = null;
    locationReconnectTimer = setTimeout(connectLocationSocket, 3000);
  };
}

export function disconnectLocationSocket(): void {
  if (locationReconnectTimer) clearTimeout(locationReconnectTimer);
  if (locationSocket) locationSocket.close();
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

export async function connectRidesSocket(): Promise<void> {
  if (ridesSocket?.readyState === WebSocket.OPEN) return;

  const token = await Storage.getToken();
  if (!token) return;

  const url = `${WS_URL}/tracking/driver-rides/?token=${token}`;

  ridesSocket = new WebSocket(url);
  ridesSocket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const type = msg.type ?? msg.event;

      if (type === "ride_offer" || type === "ride_assigned") {
        playNotificationSound();

        const isAuto = type === "ride_assigned";
        // 🔥 Trigger Local Pop-up 
        Notifications.scheduleNotificationAsync({
          content: {
            title: isAuto ? "New Ride Assigned! ⚡" : "New Ride Offer! 🚗",
            body: isAuto
              ? "You have been auto-assigned a new ride. Head to pickup!"
              : `You have a new request for ${msg.data?.rider_name || 'a passenger'}.`,
            sound: true,
            priority: Notifications.AndroidNotificationPriority.HIGH,
          },
          trigger: null, // show immediately
        });
      }

      ridesListeners.get(type)?.forEach(cb => cb(msg));
    } catch (err) { }
  };
  ridesSocket.onclose = () => {
    ridesSocket = null;
    ridesReconnectTimer = setTimeout(connectRidesSocket, 3000);
  };
}

export function disconnectRidesSocket(): void {
  if (ridesReconnectTimer) {
    clearTimeout(ridesReconnectTimer);
    ridesReconnectTimer = null;
  }
  if (ridesSocket) {
    ridesSocket.close();
    ridesSocket = null;
  }
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