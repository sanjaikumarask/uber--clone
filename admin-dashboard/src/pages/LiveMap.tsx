/// <reference types="vite/client" />
// src/pages/LiveMap.tsx  — Admin Live Map
// Tracks all drivers AND riders in real-time with detailed monitoring.
// Connects to: ws/admin/live-map/ → AdminLiveMapConsumer

import { useCallback, useEffect, useRef, useState } from "react";
import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";
import { api } from "../services/api";
import ResolutionModal from "../components/ResolutionModal";

// ── Keyframe injection (dispatch animations) ──────────────────────────────────
const DISPATCH_STYLE_ID = "dispatch-sim-styles";
if (!document.getElementById(DISPATCH_STYLE_ID)) {
  const st = document.createElement("style");
  st.id = DISPATCH_STYLE_ID;
  st.textContent = `
    @keyframes ds-pulse { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.18);opacity:0.7} }
    @keyframes ds-ring   { 0%{transform:scale(0.5);opacity:0.9} 100%{transform:scale(2.2);opacity:0} }
    @keyframes ds-shake  { 0%,100%{transform:translateX(0)} 20%{transform:translateX(-3px)} 60%{transform:translateX(3px)} }
    @keyframes ds-fadein { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
    @keyframes ds-slideup{ from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
    @keyframes ds-spin   { to{transform:rotate(360deg)} }
    .ds-pulse { animation: ds-pulse 1.1s ease-in-out infinite; }
    .ds-shake { animation: ds-shake 0.4s ease; }
    .ds-fadein{ animation: ds-fadein 0.35s ease forwards; }
    .ds-slideup{animation: ds-slideup 0.4s ease forwards;}
  `;
  document.head.appendChild(st);
}

const LIBRARIES: ("marker" | "geometry" | "places")[] = ["marker", "geometry", "places"];
const MAP_CONTAINER = { width: "100%", height: "100%" };
const DEFAULT_CENTER = { lat: 13.0827, lng: 80.2707 }; // Chennai

// ── Interfaces ──────────────────────────────────────────────────────────────

const VEHICLE_ICONS: Record<string, string> = {
  moto: "/assets/vehicles/moto.png",
  auto: "/assets/vehicles/auto.png",
  go: "/assets/vehicles/go.png",
  xl: "/assets/vehicles/xl.png",
};

interface RideInfo {
  id: number;
  status: string;
  pickup: { lat: number; lng: number };
  pickup_address?: string;
  dropoff: { lat: number; lng: number };
  drop_address?: string;
  polyline?: string;
  rider_id?: number;
  rider_name?: string;
  distance_km?: number;
  vehicle_type?: string;
  actual_distance_km?: number;
}

interface DriverPing {
  driver_id: number;
  name?: string;
  phone?: string;
  lat: number;
  lng: number;
  heading?: number | null;
  speed_kmh?: number | null;
  status: string;
  eta?: number | null;
  ts: number;
  ride?: RideInfo | null;
  offline?: boolean; // Signal to remove marker
  latency_ms?: number;
  interval_s?: number;
}

interface RiderPing {
  ride_id: number;
  rider_id: number;
  rider_name?: string;
  lat: number;
  lng: number;
  status: string;
  ts: number;
  ride?: any;
}

interface RideGraphics {
  routePolyline: google.maps.Polyline;
  progressPolyline: google.maps.Polyline;
  trailPolyline: google.maps.Polyline;  // actual path taken (breadcrumb)
  pickupMarker: google.maps.marker.AdvancedMarkerElement;
  dropoffMarker: google.maps.marker.AdvancedMarkerElement;
  toPickupPolyline: google.maps.Polyline; // From Driver current position to Pickup
}

interface DriverState extends DriverPing {
  marker: google.maps.marker.AdvancedMarkerElement;
  rideGraphics: RideGraphics | null;
  trail: google.maps.LatLng[];         // breadcrumb points
  trailPolyline: google.maps.Polyline | null; // standalone trail (no active ride)
}

interface RiderState extends RiderPing {
  marker: google.maps.marker.AdvancedMarkerElement;
}

// ── Dispatch Simulation types ────────────────────────────────────────────────
type DispatchStep = "idle" | "pickup_placed" | "notifying" | "assigned" | "ongoing";

interface DispatchDriverInfo {
  driver_id: number;
  name: string;
  dist_km: number;
  eta_min: number;
  status: "waiting" | "notified" | "accepted" | "rejected";
}

interface DispatchState {
  step: DispatchStep;
  pickup: { lat: number; lng: number } | null;
  nearbyDriverIds: number[];         // all drivers within radius
  notifiedDrivers: DispatchDriverInfo[];
  assignedDriverId: number | null;
  notifyCountdown: number;           // seconds left in NOTIFYING phase
  radiusKm: number;
}

// ── Status colors ────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  ONLINE: "#22c55e",
  OFFLINE: "#6b7280",
  BUSY: "#f59e0b",
  ASSIGNED: "#3b82f6",
  ARRIVED: "#8b5cf6",
  ONGOING: "#ef4444",
};

// ── Distance helper ───────────────────────────────────────────────────────────
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getBearing(lat1: number, lng1: number, lat2: number, lng2: number) {
  const dLon = ((lng2 - lng1) * Math.PI) / 180;
  const y = Math.sin(dLon) * Math.cos((lat2 * Math.PI) / 180);
  const x =
    Math.cos((lat1 * Math.PI) / 180) * Math.sin((lat2 * Math.PI) / 180) -
    Math.sin((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.cos(dLon);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function createPin(color: string, label: string, size = 20): HTMLElement {
  const el = document.createElement("div");
  el.style.cssText = `width:${size}px;height:${size}px;border-radius:50%;background:${color};
    color:#fff;font-size:${Math.round(size * 0.45)}px;font-weight:700;display:flex;
    align-items:center;justify-content:center;border:2px solid #fff;
    box-shadow:0 2px 6px rgba(0,0,0,0.4);`;
  el.textContent = label;
  return el;
}

function createDriverEl(ping: DriverPing): HTMLElement {
  const color = STATUS_COLOR[ping.status] ?? STATUS_COLOR.ONLINE;
  const rs = ping.ride?.status;
  const border = rs === "ARRIVED" ? "#8b5cf6" : rs === "ONGOING" ? "#ef4444" : rs === "ASSIGNED" ? "#3b82f6" : color;
  const name = ping.name || `D#${ping.driver_id}`;
  const speedTxt = ping.speed_kmh != null ? `${ping.speed_kmh.toFixed(0)} km/h` : "";

  const vType = ping.ride?.vehicle_type || "go";
  const iconUrl = VEHICLE_ICONS[vType] || VEHICLE_ICONS.go;

  const el = document.createElement("div");
  el.style.cssText = "position:relative;width:40px;height:48px;cursor:pointer;";
  el.innerHTML = `
    <img src="${iconUrl}"
      style="width:36px;height:36px;border-radius:50%;border:2px solid ${border};box-sizing:border-box;background:#fff;object-fit:contain;transition:transform 0.3s ease;" />
    <div class="s-dot" style="position:absolute;bottom:14px;right:0;width:12px;height:12px;
      border-radius:50%;background:${color};border:2px solid #000;"></div>
    <div class="d-lbl" style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);
      background:rgba(0,0,0,0.85);color:#fff;font-size:10px;font-weight:600;padding:2px 6px;
      border-radius:4px;white-space:nowrap;font-family:sans-serif;box-shadow:0 2px 4px rgba(0,0,0,0.3);">
      ${name}${rs ? ` · ${rs}` : ""}
    </div>
    <div class="d-spd" style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);
      background:rgba(0,0,0,0.75);color:#22d3ee;font-size:9px;font-weight:700;padding:1px 5px;
      border-radius:3px;white-space:nowrap;font-family:sans-serif;display:${speedTxt ? "block" : "none"}">
      ${speedTxt}
    </div>`;
  return el;
}

function createRiderEl(ping: RiderPing): HTMLElement {
  const el = document.createElement("div");
  el.style.cssText = "position:relative;width:34px;height:34px;cursor:pointer;";
  const name = ping.rider_name || `R#${ping.rider_id}`;
  el.innerHTML = `
    <div style="width:34px;height:34px;border-radius:50%;background:#276EF1;
      border:3px solid #fff;display:flex;align-items:center;justify-content:center;
      box-shadow:0 3px 8px rgba(0,0,0,0.5);font-size:17px;">👤</div>
    <div style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);
      background:rgba(39,110,241,0.9);color:#fff;font-size:10px;font-weight:700;padding:2px 6px;
      border-radius:4px;white-space:nowrap;font-family:sans-serif;box-shadow:0 2px 4px rgba(0,0,0,0.3);">
      ${name}
    </div>`;
  return el;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function AdminLiveMap() {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;
  const token = localStorage.getItem("access") ?? "";

  const { isLoaded } = useJsApiLoader({ googleMapsApiKey: apiKey, libraries: LIBRARIES, version: "beta" });

  if (isLoaded) {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes radar {
        0% { transform: scale(0.1); opacity: 1; border-width: 8px; }
        100% { transform: scale(2.5); opacity: 0; border-width: 1px; }
      }
      .radar-pulse {
        width: 20px; height: 20px;
        background: #f59e0b;
        border-radius: 50%;
        position: relative;
        box-shadow: 0 0 15px #f59e0b;
        border: 2px solid #fff;
      }
      .radar-pulse::after {
        content: '';
        position: absolute;
        top: -15px; left: -15px; right: -15px; bottom: -15px;
        border: 4px solid #f59e0b;
        border-radius: 50%;
        animation: radar 2s infinite;
      }
    `;
    if (!document.getElementById('livemap-styles')) {
      style.id = 'livemap-styles';
      document.head.appendChild(style);
    }
  }

  const mapRef = useRef<google.maps.Map | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const driversRef = useRef<Map<number, DriverState>>(new Map());
  const ridersRef = useRef<Map<number, RiderState>>(new Map());
  const reconnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const animationsRef = useRef<Map<number, number>>(new Map());
  // Track the last lat/lng used for a Directions fetch so we only re-fetch after meaningful movement
  const lastRouteFetchRef = useRef<Map<number, { lat: number; lng: number }>>(new Map());
  // Separate tracker for driver→dropoff re-routing
  const lastDropoffFetchRef = useRef<Map<number, { lat: number; lng: number }>>(new Map());

  const [driverCount, setDriverCount] = useState(0);
  const [riderCount, setRiderCount] = useState(0);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [selectedDriver, setSelectedDriver] = useState<DriverPing | null>(null);
  const [deviationAlerts, setDeviationAlerts] = useState<Map<number, { deviation_m: number; ts: number }>>(new Map());
  const deviationTimersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
  const [incidents, setIncidents] = useState<{ id: string; type: string; driver_name: string; driver_id: number; msg: string; ts: number }[]>([]);
  const [rideAction, setRideAction] = useState<{ action: "cancel" | "reassign" | "refund"; rideId: number; label: string } | null>(null);
  const [rideActionResult, setRideActionResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [rideActionLoading, setRideActionLoading] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const deadReconTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleResolutionSubmit = async (data: any) => {
    try {
      const res = await api.post("/admin/resolve-ride/", data);
      if (res.data.success) {
        setRideActionResult({ ok: true, msg: "Ride resolved and audited successfully." });
        setShowResolution(false);
        setTimeout(() => setRideActionResult(null), 4000);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.error || "Resolution failed";
      setRideActionResult({ ok: false, msg: detail });
      setShowResolution(false);
      setTimeout(() => setRideActionResult(null), 5000);
    }
  };
  // ── UI state ─────────────────────────────────────────────────────────────────
  const [driverList, setDriverList] = useState<DriverPing[]>([]);
  const [riderList, setRiderList] = useState<RiderPing[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [leftTab, setLeftTab] = useState<"drivers" | "riders" | "incidents" | "dispatch">("drivers");
  const [showTrails, setShowTrails] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);
  const [showRiders, setShowRiders] = useState(true);

  // Selected driver ref to handle sidebar updates in animations/WS
  const selectedDriverRef = useRef<DriverPing | null>(null);
  useEffect(() => { selectedDriverRef.current = selectedDriver; }, [selectedDriver]);

  // ── Ride Requests (Yellow Pulses) ──────────────────────────────────────────
  const rideRequestsRef = useRef<Map<number, google.maps.marker.AdvancedMarkerElement>>(new Map());

  // ── Dispatch Simulation state ─────────────────────────────────────────────
  const DISPATCH_RADIUS_KM = 2.5;
  const [dispatch, setDispatch] = useState<DispatchState>({
    step: "idle",
    pickup: null,
    nearbyDriverIds: [],
    notifiedDrivers: [],
    assignedDriverId: null,
    notifyCountdown: 8,
    radiusKm: DISPATCH_RADIUS_KM,
  });
  const dispatchRef = useRef<DispatchState>(dispatch);
  useEffect(() => { dispatchRef.current = dispatch; }, [dispatch]);

  // Google Maps overlay objects for dispatch
  const dispatchPickupMarkerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(null);
  const dispatchRadiusCircleRef = useRef<google.maps.Circle | null>(null);
  const dispatchRoutePolylineRef = useRef<google.maps.Polyline | null>(null);
  const dispatchTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dispatchAssignTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Demo driver IDs (reserved range — never collide with real drivers)
  const DEMO_IDS = [88801, 88802, 88803];
  const demoActiveRef = useRef(false);

  // ── Directions route helper ─────────────────────────────
  // Fetches the shortest road-following polyline from `origin` to `dest`
  // via Google Maps DirectionsService and paints it on the given Polyline object.
  function fetchRoadRoute(
    origin: { lat: number; lng: number },
    dest: { lat: number; lng: number },
    polylineObj: google.maps.Polyline,
    onEta?: (minutes: number) => void
  ) {
    const service = new google.maps.DirectionsService();
    service.route(
      {
        origin,
        destination: dest,
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (result, status) => {
        if (status === "OK" && result) {
          const path = result.routes[0].overview_path;
          polylineObj.setPath(path);
          if (onEta && result.routes[0].legs[0].duration) {
            onEta(Math.ceil(result.routes[0].legs[0].duration.value / 60));
          }
        }
      }
    );
  }

  // ── Animation Handler ───────────────────────────────────
  function animateMarker(
    marker: google.maps.marker.AdvancedMarkerElement,
    from: { lat: number, lng: number },
    to: { lat: number, lng: number },
    id: number,
    duration = 1500,
    isRider = false,
    path?: google.maps.LatLng[]
  ) {
    const key = isRider ? id + 1000000 : id;
    if (animationsRef.current.has(key)) {
      cancelAnimationFrame(animationsRef.current.get(key)!);
    }

    // --- Road Following Preparation ---
    let subPath: { lat: number, lng: number }[] = [];
    if (!isRider && path && path.length > 1) {
      try {
        const spherical = google.maps.geometry.spherical;
        const fromLatLng = new google.maps.LatLng(from.lat, from.lng);
        const toLatLng = new google.maps.LatLng(to.lat, to.lng);

        let minFromDist = Infinity;
        let fromIdx = -1;
        let minToDist = Infinity;
        let toIdx = -1;

        for (let i = 0; i < path.length; i++) {
          const dFrom = spherical.computeDistanceBetween(fromLatLng, path[i]);
          if (dFrom < minFromDist) { minFromDist = dFrom; fromIdx = i; }
          const dTo = spherical.computeDistanceBetween(toLatLng, path[i]);
          if (dTo < minToDist) { minToDist = dTo; toIdx = i; }
        }

        // Within 120m tolerance, and forward movement
        if (fromIdx !== -1 && toIdx !== -1 && fromIdx < toIdx && minFromDist < 120 && minToDist < 120) {
          subPath = [
            from,
            ...path.slice(fromIdx + 1, toIdx).map(p => ({ lat: p.lat(), lng: p.lng() })),
            to
          ];
        }
      } catch (e) { console.warn("Anim path error", e); }
    }

    const start = performance.now();

    const step = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);

      let currentPos;
      if (subPath.length > 2) {
        const totalSegments = subPath.length - 1;
        const segmentIdx = Math.min(Math.floor(progress * totalSegments), totalSegments - 1);
        const segmentProgress = (progress * totalSegments) - segmentIdx;
        currentPos = {
          lat: subPath[segmentIdx].lat + (subPath[segmentIdx + 1].lat - subPath[segmentIdx].lat) * segmentProgress,
          lng: subPath[segmentIdx].lng + (subPath[segmentIdx + 1].lng - subPath[segmentIdx].lng) * segmentProgress,
        };

        // Update heading live along sub-path
        const img = (marker.content as HTMLElement)?.querySelector("img");
        if (img) {
          const b = getBearing(subPath[segmentIdx].lat, subPath[segmentIdx].lng, subPath[segmentIdx + 1].lat, subPath[segmentIdx + 1].lng);
          img.style.transform = `rotate(${b}deg)`;
        }
      } else {
        currentPos = {
          lat: from.lat + (to.lat - from.lat) * progress,
          lng: from.lng + (to.lng - from.lng) * progress
        };
      }

      marker.position = currentPos;

      if (progress < 1) {
        animationsRef.current.set(key, requestAnimationFrame(step));
      } else {
        animationsRef.current.delete(key);
      }
    };
    animationsRef.current.set(key, requestAnimationFrame(step));
  }

  // ── Handlers ───────────────────────────────────────────

  function handleDriverUpdate(ping: DriverPing) {
    const map = mapRef.current;
    if (!map) return;

    // 🛑 If we are in the middle of a "Track Trip" simulation, ignore 
    // background server pings for the assigned driver so they don't jump.
    if (dispatchRef.current.step === "ongoing" && dispatchRef.current.assignedDriverId === ping.driver_id) {
      return;
    }

    if (ping.offline) {
      const d = driversRef.current.get(ping.driver_id);
      if (d) {
        d.marker.map = null;
        // Clean up ride graphics
        if (d.rideGraphics) {
          d.rideGraphics.routePolyline.setMap(null);
          d.rideGraphics.progressPolyline.setMap(null);
          d.rideGraphics.trailPolyline.setMap(null);
          d.rideGraphics.pickupMarker.map = null;
          d.rideGraphics.dropoffMarker.map = null;
        }
        // Clean up standalone trail
        if (d.trailPolyline) d.trailPolyline.setMap(null);
        driversRef.current.delete(ping.driver_id);
        setDriverCount(driversRef.current.size);
        if (selectedDriverRef.current?.driver_id === ping.driver_id) setSelectedDriver(null);
      }
      return;
    }

    const existing = driversRef.current.get(ping.driver_id);

    // 🚫 Out-of-order rejection: If timestamp is older than what we have, discard.
    if (existing && ping.ts && existing.ts && ping.ts <= existing.ts) return;

    let rideGraphics = existing?.rideGraphics ?? null;

    if (ping.ride && !rideGraphics) {
      // Decode backend polyline if provided; otherwise empty — we'll fetch via Directions below
      const path = ping.ride.polyline ? google.maps.geometry.encoding.decodePath(ping.ride.polyline) : [];
      rideGraphics = {
        // Grey ghost route: full planned route (pickup → dropoff)
        routePolyline: new google.maps.Polyline({
          path, map,
          strokeColor: "#334155", strokeOpacity: 0.55, strokeWeight: 5, zIndex: 1,
          icons: [{
            icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 1.5, strokeColor: "#64748b", fillColor: "#64748b", fillOpacity: 0.6 },
            repeat: "80px",
          }],
        }),
        // Blue road-following route: driver current pos → dropoff (re-fetched via Directions API)
        progressPolyline: new google.maps.Polyline({
          path: [], map,
          strokeColor: "#276EF1", strokeOpacity: 0.95, strokeWeight: 5, zIndex: 2,
          icons: [{
            icon: { path: google.maps.SymbolPath.FORWARD_OPEN_ARROW, scale: 2.2, strokeColor: "#276EF1", fillColor: "#276EF1", fillOpacity: 1 },
            repeat: "55px",
            offset: "10px",
          }],
        }),
        trailPolyline: new google.maps.Polyline({
          path: [], map,
          strokeColor: "#22d3ee",
          strokeOpacity: 0.7,
          strokeWeight: 3,
          zIndex: 3,
          icons: [{
            icon: { path: google.maps.SymbolPath.FORWARD_OPEN_ARROW, scale: 1.8, strokeColor: "#22d3ee" },
            repeat: "60px",
          }],
        }),
        pickupMarker: new google.maps.marker.AdvancedMarkerElement({
          position: ping.ride.pickup, map, title: `Pickup #${ping.ride.id}`,
          content: createPin("#22c55e", "P"),
        }),
        dropoffMarker: new google.maps.marker.AdvancedMarkerElement({
          position: ping.ride.dropoff, map, title: `Dropoff #${ping.ride.id}`,
          content: createPin("#ef4444", "D"),
        }),
        toPickupPolyline: new google.maps.Polyline({
          path: [],
          map,
          strokeColor: "#f97316",
          strokeOpacity: 0.92,
          strokeWeight: 5,
          zIndex: 4,
          icons: [{
            icon: { path: google.maps.SymbolPath.FORWARD_OPEN_ARROW, scale: 2, strokeColor: "#f97316", fillColor: "#f97316", fillOpacity: 1 },
            repeat: "50px",
            offset: "10px",
          }],
        }),
      };

      if (ping.ride && rideGraphics && !existing?.rideGraphics) {
        // 1) Driver → pickup (orange road route)
        fetchRoadRoute(
          { lat: ping.lat, lng: ping.lng },
          ping.ride.pickup,
          rideGraphics.toPickupPolyline,
          (minutes) => {
            const d = driversRef.current.get(ping.driver_id);
            if (d) {
              d.eta = minutes;
              if (selectedDriverRef.current?.driver_id === ping.driver_id) setSelectedDriver({ ...d });
              setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
            }
          }
        );
        lastRouteFetchRef.current.set(ping.driver_id, { lat: ping.lat, lng: ping.lng });

        // 2) Full route: pickup → dropoff (grey ghost, used when backend polyline missing)
        if (!ping.ride.polyline) {
          fetchRoadRoute(ping.ride.pickup, ping.ride.dropoff, rideGraphics.routePolyline);
        }

        // 3) Driver → dropoff road route (blue live route for ONGOING rides)
        if (ping.ride.status === "ONGOING") {
          fetchRoadRoute(
            { lat: ping.lat, lng: ping.lng },
            ping.ride.dropoff,
            rideGraphics.progressPolyline,
            (minutes) => {
              const d = driversRef.current.get(ping.driver_id);
              if (d) {
                d.eta = minutes;
                if (selectedDriverRef.current?.driver_id === ping.driver_id) setSelectedDriver({ ...d });
                setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
              }
            }
          );
          lastDropoffFetchRef.current.set(ping.driver_id, { lat: ping.lat, lng: ping.lng });
        }
      }

    } else if (!ping.ride && rideGraphics) {
      rideGraphics.routePolyline.setMap(null);
      rideGraphics.progressPolyline.setMap(null);
      rideGraphics.trailPolyline.setMap(null);
      rideGraphics.toPickupPolyline.setMap(null);
      rideGraphics.pickupMarker.map = null;
      rideGraphics.dropoffMarker.map = null;
      lastRouteFetchRef.current.delete(ping.driver_id);
      rideGraphics = null;
    }

    if (existing) {
      const from = { lat: existing.lat, lng: existing.lng };
      const to = { lat: ping.lat, lng: ping.lng };

      // 3️⃣ Metrics Calculation
      ping.latency_ms = Math.max(0, Date.now() - (ping.ts * 1000));
      if (existing.ts) ping.interval_s = ping.ts - existing.ts;

      // 1️⃣ Dynamic Duration (Interpolation)
      // ping.ts is in seconds. If delta is 5s, we want ~4800ms animation (leaving a tiny buffer).
      let duration = 2000; // default
      if (ping.ts && existing.ts && ping.ts > existing.ts) {
        const deltaMs = (ping.ts - existing.ts) * 1000;
        duration = Math.min(Math.max(800, deltaMs * 0.95), 8000);
      }

      // 2️⃣ Speed Smoothing (EMA)
      let smoothedSpeed = ping.speed_kmh;
      if (ping.speed_kmh != null && existing.speed_kmh != null) {
        smoothedSpeed = (0.7 * ping.speed_kmh) + (0.3 * existing.speed_kmh);
      }
      ping.speed_kmh = smoothedSpeed;

      let rot = ping.heading;
      if (rot == null && (from.lat !== to.lat || from.lng !== to.lng))
        rot = getBearing(from.lat, from.lng, to.lat, to.lng);

      const el = existing.marker.content as HTMLElement;
      const dot = el.querySelector(".s-dot") as HTMLElement | null;
      const img = el.querySelector("img") as HTMLImageElement | null;
      const lbl = el.querySelector(".d-lbl") as HTMLElement | null;
      const spd = el.querySelector(".d-spd") as HTMLElement | null;
      const c = STATUS_COLOR[ping.status] ?? STATUS_COLOR.ONLINE;
      const rs = ping.ride?.status;
      const name = ping.name || existing.name || `D#${ping.driver_id}`;
      const brd = rs === "ARRIVED" ? "#8b5cf6" : rs === "ONGOING" ? "#ef4444" : rs === "ASSIGNED" ? "#3b82f6" : c;

      const vType = ping.ride?.vehicle_type || "go";
      const iconUrl = VEHICLE_ICONS[vType] || VEHICLE_ICONS.go;

      if (dot) dot.style.background = c;
      if (img) {
        img.style.borderColor = brd;
        // Check if icon needs to change (comparing relative paths)
        if (!img.src.includes(iconUrl)) {
          img.src = iconUrl;
        }
        if (rot != null) img.style.transform = `rotate(${rot}deg)`;
      }
      if (lbl) lbl.textContent = `${name}${rs ? ` · ${rs}` : ""}`;
      // Update speed badge with smoothed value
      if (spd) {
        if (ping.speed_kmh != null) {
          spd.textContent = `${ping.speed_kmh.toFixed(0)} km/h`;
          spd.style.display = "block";
        } else {
          spd.style.display = "none";
        }
      }

      const routePath = rideGraphics?.routePolyline?.getPath()?.getArray() || [];
      animateMarker(existing.marker, from, to, ping.driver_id, duration, false, routePath);

      // ── Blue road-following route: driver → dropoff (re-routed live every ~80m) ──
      if (rideGraphics?.progressPolyline && ping.ride?.status === "ONGOING") {
        rideGraphics.progressPolyline.setMap(map);
        const lastDropoff = lastDropoffFetchRef.current.get(ping.driver_id);
        const movedEnoughDropoff = !lastDropoff ||
          Math.abs(ping.lat - lastDropoff.lat) > 0.00072 || // ~80m
          Math.abs(ping.lng - lastDropoff.lng) > 0.00072;
        if (movedEnoughDropoff) {
          fetchRoadRoute(
            { lat: ping.lat, lng: ping.lng },
            ping.ride.dropoff,
            rideGraphics.progressPolyline,
            (minutes) => {
              const d = driversRef.current.get(ping.driver_id);
              if (d) {
                d.eta = minutes;
                if (selectedDriverRef.current?.driver_id === ping.driver_id) setSelectedDriver({ ...d });
                setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
              }
            }
          );
          lastDropoffFetchRef.current.set(ping.driver_id, { lat: ping.lat, lng: ping.lng });
        }
      } else if (rideGraphics?.progressPolyline && ping.ride?.status !== "ONGOING") {
        rideGraphics.progressPolyline.setMap(null);
      }

      // ── Orange road-following route: driver → pickup (re-fetched every ~30m) ──
      if (rideGraphics?.toPickupPolyline) {
        if (ping.ride?.status === "ASSIGNED" || ping.ride?.status === "ARRIVED") {
          rideGraphics.toPickupPolyline.setMap(map);

          const lastFetch = lastRouteFetchRef.current.get(ping.driver_id);
          const movedEnough = !lastFetch ||
            Math.abs(ping.lat - lastFetch.lat) > 0.00027 || // ~30m
            Math.abs(ping.lng - lastFetch.lng) > 0.00027;

          if (movedEnough) {
            fetchRoadRoute(
              { lat: ping.lat, lng: ping.lng },
              ping.ride.pickup,
              rideGraphics.toPickupPolyline,
              (minutes) => {
                const d = driversRef.current.get(ping.driver_id);
                if (d) {
                  d.eta = minutes;
                  if (selectedDriverRef.current?.driver_id === ping.driver_id) setSelectedDriver({ ...d });
                  setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
                }
              }
            );
            lastRouteFetchRef.current.set(ping.driver_id, { lat: ping.lat, lng: ping.lng });
          }
        } else {
          rideGraphics.toPickupPolyline.setMap(null);
        }
      }

      // 4️⃣ Auto-Fit Bounds (Optional but helpful for admin)
      if (ping.ride && (ping.ride.status === "ASSIGNED" || ping.ride.status === "ONGOING")) {
        const bounds = new google.maps.LatLngBounds();
        bounds.extend({ lat: ping.lat, lng: ping.lng });
        if (ping.ride.status === "ASSIGNED") bounds.extend(ping.ride.pickup);
        else bounds.extend(ping.ride.dropoff);

        // Only fit if the driver is selected
        if (selectedDriverRef.current?.driver_id === ping.driver_id) {
          map.fitBounds(bounds, { top: 100, right: 100, bottom: 100, left: 100 });
        }
      }

      // Append to trail (cyan breadcrumb of actual path taken)
      const newPoint = new google.maps.LatLng(ping.lat, ping.lng);
      const trail = [...existing.trail, newPoint].slice(-150); // cap at 150 points
      if (rideGraphics?.trailPolyline) {
        rideGraphics.trailPolyline.setPath(trail);
      } else if (existing.trailPolyline) {
        existing.trailPolyline.setPath(trail);
      }

      const updatedState: DriverState = { ...existing, ...ping, marker: existing.marker, rideGraphics, trail, trailPolyline: existing.trailPolyline };
      driversRef.current.set(ping.driver_id, updatedState);
      if (selectedDriverRef.current?.driver_id === ping.driver_id) setSelectedDriver(updatedState);
      setDriverList(Array.from(driversRef.current.values()).map(d => ({ ...d })));
    } else {
      // Brand new driver — create trail polyline for non-ride tracking
      const standaloneTrail = new google.maps.Polyline({
        path: [], map,
        strokeColor: "#22d3ee",
        strokeOpacity: 0.7,
        strokeWeight: 3,
        zIndex: 3,
      });
      const el = createDriverEl(ping);
      const marker = new google.maps.marker.AdvancedMarkerElement({
        position: { lat: ping.lat, lng: ping.lng }, content: el, map, title: `Driver #${ping.driver_id}`,
      });
      const driverData: DriverState = { ...ping, marker, rideGraphics, trail: [], trailPolyline: standaloneTrail };
      el.addEventListener("click", () => { const d = driversRef.current.get(ping.driver_id) || driverData; setSelectedDriver(d); mapRef.current?.panTo({ lat: d.lat, lng: d.lng }); });
      driversRef.current.set(ping.driver_id, driverData);
      setDriverCount(driversRef.current.size);
      setDriverList(Array.from(driversRef.current.values()).map(d => ({ ...d })));

      if (driversRef.current.size === 1) {
        const ctr = map.getCenter();
        if (ctr && Math.abs(ctr.lat() - DEFAULT_CENTER.lat) < 0.01) {
          map.panTo({ lat: ping.lat, lng: ping.lng });
          map.setZoom(14);
        }
      }
    }
  }

  function handleRiderUpdate(ping: RiderPing) {
    const map = mapRef.current;
    if (!map) return;

    // 1. Manage Pulse (Yellow Radar)
    const rideId = ping.ride_id || ping.ride?.id;
    if (rideId) {
      if (["SEARCHING", "OFFERED"].includes(ping.status)) {
        if (!rideRequestsRef.current.has(rideId)) {
          console.log("[AdminLiveMap] 🟡 handleRiderUpdate — adding pulse for Ride", rideId);
          const el = document.createElement("div");
          el.className = "radar-pulse";
          const vType = ping.ride?.vehicle_type || "go";
          const iconUrl = VEHICLE_ICONS[vType as keyof typeof VEHICLE_ICONS] || VEHICLE_ICONS.go;
          el.innerHTML = `<img src="${iconUrl}" style="width:12px; height:12px; position:absolute; top:4px; left:4px; z-index:1; object-fit:contain;" />`;
          const marker = new google.maps.marker.AdvancedMarkerElement({
            position: { lat: ping.lat, lng: ping.lng },
            map,
            content: el,
            title: `Searching Ride #${rideId}`,
          });
          marker.addListener("click", () => mapRef.current?.panTo({ lat: ping.lat, lng: ping.lng }));
          rideRequestsRef.current.set(rideId, marker);
        } else {
          // Move existing pulse if rider moves
          const marker = rideRequestsRef.current.get(rideId);
          if (marker) marker.position = { lat: ping.lat, lng: ping.lng };
        }
      } else if (["ASSIGNED", "ONGOING", "COMPLETED", "CANCELLED", "NO_SHOW"].includes(ping.status)) {
        const marker = rideRequestsRef.current.get(rideId);
        if (marker) {
          console.log("[AdminLiveMap] ⚪ handleRiderUpdate — removing pulse for Ride", rideId, "stat:", ping.status);
          marker.map = null;
          rideRequestsRef.current.delete(rideId);
        }
      }
    }

    // 2. Manage Rider Marker & Sidebar
    const existing = ridersRef.current.get(ping.rider_id);
    if (existing) {
      let duration = 2000;
      if (ping.ts && existing.ts && ping.ts > existing.ts) {
        duration = Math.min(Math.max(1000, (ping.ts - existing.ts) * 950), 10000);
      }
      animateMarker(existing.marker, { lat: existing.lat, lng: existing.lng }, { lat: ping.lat, lng: ping.lng }, ping.rider_id, duration, true);
      const updated = { ...existing, ...ping };
      ridersRef.current.set(ping.rider_id, updated);
      setRiderList(Array.from(ridersRef.current.values()).map(r => ({ ...r })));
    } else {
      const el = createRiderEl(ping);
      const marker = new google.maps.marker.AdvancedMarkerElement({
        position: { lat: ping.lat, lng: ping.lng }, content: el, map, title: `Rider #${ping.rider_id}`,
      });
      const riderData = { ...ping, marker };
      ridersRef.current.set(ping.rider_id, riderData);
      setRiderCount(ridersRef.current.size);
      setRiderList(Array.from(ridersRef.current.values()).map(r => ({ ...r })));
    }
  }

  // Ref-based handlers for WebSocket closure
  const handlersRef = useRef({ handleDriverUpdate, handleRiderUpdate });
  useEffect(() => { handlersRef.current = { handleDriverUpdate, handleRiderUpdate }; });

  function handleDeviationAlert(data: { driver_id: number; deviation_m: number; ts: number; driver_name?: string }) {
    setDeviationAlerts((prev: Map<number, { deviation_m: number; ts: number }>) => {
      const next = new Map(prev);
      next.set(data.driver_id, { deviation_m: data.deviation_m, ts: data.ts });
      return next;
    });

    // Push to global incident log
    setIncidents((prev: any[]) => [
      {
        id: Math.random().toString(36).substr(2, 9),
        type: "DEVIATION",
        driver_id: data.driver_id,
        driver_name: data.driver_name || `Driver #${data.driver_id}`,
        msg: `Off-route by ${data.deviation_m}m`,
        ts: data.ts
      },
      ...prev.slice(0, 49) // Keep last 50
    ]);

    // Auto-clear banner after 30 seconds
    if (deviationTimersRef.current.has(data.driver_id)) {
      clearTimeout(deviationTimersRef.current.get(data.driver_id)!);
    }
    const t = setTimeout(() => {
      setDeviationAlerts((prev: Map<number, { deviation_m: number; ts: number }>) => { const n = new Map(prev); n.delete(data.driver_id); return n; });
      deviationTimersRef.current.delete(data.driver_id);
    }, 30000);
    deviationTimersRef.current.set(data.driver_id, t);
  }

  function clearAllMapData() {
    driversRef.current.forEach(d => {
      d.marker.map = null;
      if (d.rideGraphics) {
        d.rideGraphics.routePolyline.setMap(null);
        d.rideGraphics.progressPolyline.setMap(null);
        d.rideGraphics.trailPolyline.setMap(null);
        d.rideGraphics.pickupMarker.map = null;
        d.rideGraphics.dropoffMarker.map = null;
      }
      if (d.trailPolyline) d.trailPolyline.setMap(null);
    });
    driversRef.current.clear();
    ridersRef.current.forEach(r => { r.marker.map = null; });
    ridersRef.current.clear();
    setDriverCount(0);
    setRiderCount(0);
    setSelectedDriver(null);
    setIncidents([]);
    setDeviationAlerts(new Map());
  }

  function connect() {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/admin/live-map/?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setWsStatus("connecting");
    ws.onopen = () => { console.log("[AdminLiveMap] connected"); setWsStatus("connected"); };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "FLEET_RESET") {
          clearAllMapData();
          return;
        }

        const { handleDriverUpdate: hdu } = handlersRef.current;
        if ((msg.type === "DRIVER_LOCATION_UPDATED" || msg.type === "driver_location_update" || msg.type === "location_update") && msg.data) safeHandleDriverUpdate(msg.data);
        else if ((msg.type === "RIDER_LOCATION_UPDATED" || msg.type === "rider_location_update" || msg.type === "location_updated") && msg.data) safeHandleRiderUpdate(msg.data);
        else if (msg.type === "ROUTE_DEVIATION" && msg.data) handleDeviationAlert(msg.data);
        else if (msg.type === "RIDE_CREATED" && msg.data) {
          const d = msg.data;
          // 🆕 Simply forward to safeHandleRiderUpdate which handles pulse + sidebar
          if (d.ride_id && d.rider_id && d.pickup) {
            safeHandleRiderUpdate({
              ride_id: d.ride_id,
              rider_id: d.rider_id,
              rider_name: d.rider_name || `Rider #${d.rider_id}`,
              lat: parseFloat(d.pickup.lat),
              lng: parseFloat(d.pickup.lng),
              status: "SEARCHING",
              ts: Math.floor(Date.now() / 1000),
              ride: {
                id: d.ride_id,
                vehicle_type: d.vehicle_type,
                pickup: d.pickup
              }
            });
          }
        }
        else if (msg.type === "RIDE_STATUS_UPDATED" && msg.data) {
          const d = msg.data;
          const existing = d.driver_id ? driversRef.current.get(d.driver_id) : null;
          if (existing) {
            // ✅ Update existing driver marker
            hdu({
              ...existing,
              status: d.driver_status || (["COMPLETED", "CANCELLED"].includes(d.status) ? "ONLINE" : existing.status),
              ride: (["COMPLETED", "CANCELLED"].includes(d.status)) ? null : (d.ride || existing.ride)
            });
          } else if (d.driver_id && d.ride?.pickup) {
            // ✅ NEW FIX: New ride assigned to a driver who has no marker yet.
            console.log("[AdminLiveMap] 🆕 New ride for unseen driver", d.driver_id, "— creating marker from RIDE_STATUS_UPDATED");
            hdu({
              driver_id: d.driver_id,
              name: d.driver_name || `Driver #${d.driver_id}`,
              phone: d.driver_phone || "",
              lat: d.ride.pickup.lat,
              lng: d.ride.pickup.lng,
              heading: null,
              speed_kmh: null,
              status: d.driver_status || "BUSY",
              ts: Math.floor(Date.now() / 1000),
              ride: d.ride,
            });
          }

          const rideId = d.ride_id || d.ride?.id;
          if (rideId) {
            if (d.nearby_driver_ids) {
              applyDriverGlow(d.nearby_driver_ids, d.driver_id || null, []);
            }

            // Forward status to handleRiderUpdate so it can manage the sidebar/pulse/marker
            if (d.rider_id) {
              safeHandleRiderUpdate({
                ride_id: rideId,
                rider_id: d.rider_id,
                rider_name: d.rider_name || `Rider #${d.rider_id}`,
                lat: d.ride?.pickup?.lat || 0,
                lng: d.ride?.pickup?.lng || 0,
                status: d.status,
                ts: Math.floor(Date.now() / 1000),
                ride: d.ride
              });
            }

            if (["COMPLETED", "CANCELLED", "NO_SHOW"].includes(d.status)) {
              applyDriverGlow([], null, []);
            }
          }
        }
      } catch (e) {
        console.error("[AdminLiveMap] msg error", e);
      }
    };

    ws.onclose = () => {
      setWsStatus("disconnected");
      wsRef.current = null;
      reconnTimer.current = setTimeout(connect, 3000);

      // Clear stale markers on disconnect so reconnection brings fresh snapshot
      driversRef.current.forEach(d => {
        d.marker.map = null;
        if (d.rideGraphics) {
          d.rideGraphics.routePolyline.setMap(null); d.rideGraphics.progressPolyline.setMap(null);
          d.rideGraphics.trailPolyline.setMap(null);
          d.rideGraphics.pickupMarker.map = null; d.rideGraphics.dropoffMarker.map = null;
          if (d.rideGraphics.toPickupPolyline) d.rideGraphics.toPickupPolyline.setMap(null);
        }
        if (d.trailPolyline) d.trailPolyline.setMap(null);
      });
      driversRef.current.clear();
      setDriverCount(0);

      ridersRef.current.forEach(r => r.marker.map = null);
      ridersRef.current.clear();
      setRiderCount(0);
    };
  }

  // ── Map-ready race condition fix ─────────────────────────────────────────
  // WebSocket connects immediately (in useEffect) but the GoogleMap onLoad
  // fires asynchronously — sometimes AFTER the first WS messages arrive.
  // Any handleDriverUpdate / handleRiderUpdate called while mapRef.current
  // is null silently returns without creating markers.
  //
  // Fix: buffer incoming messages in pendingRef and flush them once the map
  // is ready. This ref is consumed in the GoogleMap onLoad callback below.
  const pendingRef = useRef<Array<() => void>>([]);
  const mapReadyRef = useRef(false);

  function flushPending() {
    const pending = pendingRef.current.splice(0);
    pending.forEach(fn => fn());
  }

  // Wrap handlersRef so that calls before map-ready are queued, not dropped
  const safeHandleDriverUpdate = (ping: DriverPing) => {
    if (mapReadyRef.current) {
      handlersRef.current.handleDriverUpdate(ping);
    } else {
      pendingRef.current.push(() => handlersRef.current.handleDriverUpdate(ping));
    }
  };

  const safeHandleRiderUpdate = (ping: RiderPing) => {
    if (mapReadyRef.current) {
      handlersRef.current.handleRiderUpdate(ping);
    } else {
      pendingRef.current.push(() => handlersRef.current.handleRiderUpdate(ping));
    }
  };

  useEffect(() => {
    // 🔮 Dead Reckoning Loop: Every 2 seconds, nudge moving drivers if no packet arrived
    deadReconTimerRef.current = setInterval(() => {
      const now = Date.now();
      driversRef.current.forEach((d, id) => {
        // If speed > 10kmh and no update for > 3.5s and not currently rider
        const lastArrival = d.ts * 1000;
        if (now - lastArrival > 3500 && (d.speed_kmh ?? 0) > 10 && d.heading != null) {
          if (animationsRef.current.has(id)) return; // Don't fight active animation

          const distancePerInterval = (d.speed_kmh! / 3.6) * 1; // 1 second nudge
          const rad = (d.heading * Math.PI) / 180;
          const deltaLat = (distancePerInterval * Math.cos(rad)) / 111111;
          const deltaLng = (distancePerInterval * Math.sin(rad)) / (111111 * Math.cos((d.lat * Math.PI) / 180));

          const to = { lat: d.lat + deltaLat, lng: d.lng + deltaLng };

          // Add "PREDICTED" badge visually
          const el = d.marker.content as HTMLElement;
          const lbl = el.querySelector(".d-lbl") as HTMLElement | null;
          if (lbl && !lbl.textContent?.includes("🔮")) lbl.textContent = "🔮 " + lbl.textContent;

          animateMarker(d.marker, { lat: d.lat, lng: d.lng }, to, id, 1000);
          d.lat = to.lat; d.lng = to.lng; // Update local state for next nudge
        }
      });
    }, 1500);

    connect();
    return () => {
      if (reconnTimer.current) clearTimeout(reconnTimer.current);
      if (deadReconTimerRef.current) clearInterval(deadReconTimerRef.current);
      wsRef.current?.close();
      driversRef.current.forEach(d => {
        d.marker.map = null;
        if (d.rideGraphics) {
          d.rideGraphics.routePolyline.setMap(null); d.rideGraphics.progressPolyline.setMap(null);
          d.rideGraphics.trailPolyline.setMap(null);
          d.rideGraphics.pickupMarker.map = null; d.rideGraphics.dropoffMarker.map = null;
        }
        if (d.trailPolyline) d.trailPolyline.setMap(null);
      });
      ridersRef.current.forEach(r => r.marker.map = null);
    };
  }, []);

  // ── Dispatch Simulation logic ─────────────────────────────────────────────

  /** Paint / update glow on nearby drivers */
  function applyDriverGlow(nearbyIds: number[], assignedId: number | null, notifiedDrivers: DispatchDriverInfo[]) {
    driversRef.current.forEach((d, id) => {
      const el = d.marker.content as HTMLElement;
      const img = el.querySelector("img") as HTMLElement | null;
      if (!img) return;
      const isNearby = nearbyIds.includes(id);
      const isAssigned = id === assignedId;
      const info = notifiedDrivers.find(nd => nd.driver_id === id);
      if (isAssigned) {
        img.style.border = "3px solid #22c55e";
        img.style.boxShadow = "0 0 20px #22c55e, 0 0 40px #22c55e88";
        img.style.filter = "drop-shadow(0 0 8px #22c55e)";
        el.style.zIndex = "9999";
        el.classList.remove("ds-pulse");
      } else if (isNearby && assignedId === null) {
        const notifyColor = info?.status === "notified" ? "#f59e0b" : "#3b82f6";
        img.style.border = `3px solid ${notifyColor}`;
        img.style.boxShadow = `0 0 14px ${notifyColor}, 0 0 28px ${notifyColor}66`;
        img.style.filter = `drop-shadow(0 0 6px ${notifyColor})`;
        el.style.zIndex = "500";
        el.classList.add("ds-pulse");
      } else {
        img.style.border = "2px solid #fff";
        img.style.boxShadow = "";
        img.style.filter = "";
        el.style.zIndex = "";
        el.classList.remove("ds-pulse");
      }
    });
  }

  /** Clear all dispatch overlays */
  function clearDispatchOverlays() {
    if (dispatchPickupMarkerRef.current) { dispatchPickupMarkerRef.current.map = null; dispatchPickupMarkerRef.current = null; }
    if (dispatchRadiusCircleRef.current) { dispatchRadiusCircleRef.current.setMap(null); dispatchRadiusCircleRef.current = null; }
    if (dispatchRoutePolylineRef.current) { dispatchRoutePolylineRef.current.setMap(null); dispatchRoutePolylineRef.current = null; }
    if (dispatchTimerRef.current) { clearInterval(dispatchTimerRef.current); dispatchTimerRef.current = null; }
    if (dispatchAssignTimerRef.current) { clearTimeout(dispatchAssignTimerRef.current); dispatchAssignTimerRef.current = null; }

    // Strip classes from all markers
    document.querySelectorAll(".ds-glow, .ds-glow-win").forEach(el => el.classList.remove("ds-glow", "ds-glow-win"));
    applyDriverGlow([], null, []);
  }

  /** STEP 1 → 2: Place pickup marker + radius circle on map center */
  const startDispatchSim = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    clearDispatchOverlays();

    const center = map.getCenter()!;
    const pickup = { lat: center.lat(), lng: center.lng() };

    // Pickup pin
    const pinEl = document.createElement("div");
    pinEl.innerHTML = `
      <div style="position:relative;width:48px;height:56px;">
        <div class="ds-pulse" style="width:48px;height:48px;border-radius:50%;background:rgba(59,130,246,0.25);border:2px solid #3b82f6;display:flex;align-items:center;justify-content:center;box-shadow:0 0 20px #3b82f6, 0 0 40px #3b82f630;">
          <div style="width:20px;height:20px;border-radius:50%;background:#3b82f6;"></div>
        </div>
        <div style="position:absolute;top:-24px;left:50%;transform:translateX(-50%);background:#3b82f6;color:#fff;font-size:9px;font-weight:800;padding:3px 8px;border-radius:4px;white-space:nowrap;letter-spacing:0.5px;">📍 PICKUP REQUEST</div>
      </div>`;
    dispatchPickupMarkerRef.current = new google.maps.marker.AdvancedMarkerElement({
      position: pickup, map, title: "Pickup Request", content: pinEl,
    });

    // Radius circle
    dispatchRadiusCircleRef.current = new google.maps.Circle({
      center: pickup, radius: DISPATCH_RADIUS_KM * 1000, map,
      strokeColor: "#3b82f6", strokeOpacity: 0.9, strokeWeight: 2,
      fillColor: "#3b82f6", fillOpacity: 0.07,
    });

    // Find nearby ONLINE drivers
    const nearby: DispatchDriverInfo[] = [];
    driversRef.current.forEach((d) => {
      if (d.status !== "ONLINE" && d.status !== "BUSY") return;
      if (d.ride) return; // already on a ride
      const dist = haversineKm(pickup.lat, pickup.lng, d.lat, d.lng);
      if (dist <= DISPATCH_RADIUS_KM) {
        nearby.push({
          driver_id: d.driver_id,
          name: d.name || `Driver #${d.driver_id}`,
          dist_km: Math.round(dist * 10) / 10,
          eta_min: Math.ceil((dist / 25) * 60),
          status: "waiting",
        });
      }
    });
    nearby.sort((a, b) => a.dist_km - b.dist_km);

    const nearbyIds = nearby.map(n => n.driver_id);
    applyDriverGlow(nearbyIds, null, nearby);

    const initialDispatch: DispatchState = {
      step: "pickup_placed",
      pickup,
      nearbyDriverIds: nearbyIds,
      notifiedDrivers: nearby,
      assignedDriverId: null,
      notifyCountdown: 8,
      radiusKm: DISPATCH_RADIUS_KM,
    };
    setDispatch(initialDispatch);
    dispatchRef.current = initialDispatch;
    setLeftTab("dispatch");

    // Auto-advance to NOTIFYING after 1.5s
    setTimeout(() => {
      const notified = dispatchRef.current.notifiedDrivers.map(d => ({ ...d, status: "notified" as const }));
      const notifyState: DispatchState = { ...dispatchRef.current, step: "notifying", notifiedDrivers: notified };
      setDispatch(notifyState);
      dispatchRef.current = notifyState;
      applyDriverGlow(nearbyIds, null, notified);

      // Countdown
      if (dispatchTimerRef.current) clearInterval(dispatchTimerRef.current);
      dispatchTimerRef.current = setInterval(() => {
        const cur = dispatchRef.current;
        const next = cur.notifyCountdown - 1;
        if (next <= 0) {
          clearInterval(dispatchTimerRef.current!);
          dispatchTimerRef.current = null;
          // Auto-assign nearest driver
          assignDriver();
        } else {
          const s = { ...cur, notifyCountdown: next };
          setDispatch(s);
          dispatchRef.current = s;
        }
      }, 1000);
    }, 1500);
  }, []);

  /** STEP 3 → 4: Assign nearest driver */
  const assignDriver = useCallback(() => {
    const cur = dispatchRef.current;
    if (cur.notifiedDrivers.length === 0) { resetDispatch(); return; }
    clearInterval(dispatchTimerRef.current!);
    dispatchTimerRef.current = null;

    const sorted = [...cur.notifiedDrivers].sort((a, b) => a.dist_km - b.dist_km);
    const winner = sorted[0];
    const rejected = sorted.slice(1).map(d => ({ ...d, status: "rejected" as const }));
    const updated = [{ ...winner, status: "accepted" as const }, ...rejected];

    applyDriverGlow(cur.nearbyDriverIds, winner.driver_id, updated);

    // Draw route from assigned driver to pickup
    const driverState = driversRef.current.get(winner.driver_id);
    const map = mapRef.current;
    if (driverState && map && cur.pickup) {
      const svc = new google.maps.DirectionsService();
      svc.route(
        { origin: { lat: driverState.lat, lng: driverState.lng }, destination: cur.pickup, travelMode: google.maps.TravelMode.DRIVING },
        (result, status) => {
          if (status === "OK" && result) {
            if (dispatchRoutePolylineRef.current) dispatchRoutePolylineRef.current.setMap(null);
            dispatchRoutePolylineRef.current = new google.maps.Polyline({
              path: result.routes[0].overview_path, map,
              strokeColor: "#22c55e", strokeOpacity: 0.95, strokeWeight: 5, zIndex: 10,
              icons: [{ icon: { path: google.maps.SymbolPath.FORWARD_OPEN_ARROW, scale: 2.5, strokeColor: "#22c55e" }, repeat: "50px" }],
            });
          }
        }
      );
    }

    const assignedState: DispatchState = { ...cur, step: "assigned", notifiedDrivers: updated, assignedDriverId: winner.driver_id, notifyCountdown: 0 };
    setDispatch(assignedState);
    dispatchRef.current = assignedState;

    if (driverState && cur.pickup) {
      // Inject mock ride so the detail panel shows the "Assigned" ride
      driverState.ride = {
        id: 77000 + winner.driver_id,
        status: "ASSIGNED",
        pickup: { lat: cur.pickup.lat, lng: cur.pickup.lng },
        dropoff: { lat: cur.pickup.lat + 0.02, lng: cur.pickup.lng + 0.02 },
        pickup_address: "Pickup: Chennai City Center",
        drop_address: "Dropoff: Anna Nagar West",
        vehicle_type: "go",
        rider_id: 1,
        rider_name: "John Doe",
        distance_km: winner.dist_km,
        actual_distance_km: 0,
      };

      // Auto-select the winner so user sees the details
      setSelectedDriver({ ...driverState });

      // Update global list
      setDriverCount(driversRef.current.size);
      setDriverList(Array.from(driversRef.current.values()).map(d => ({ ...d })));
    }
  }, []);

  /** Animate a driver marker along a series of coordinates */
  const animateAlongPath = useCallback(async (driverId: number, path: google.maps.LatLng[], status: string, speed_kmh: number) => {
    const d = driversRef.current.get(driverId);
    if (!d) return;

    for (let i = 0; i < path.length - 1; i++) {
      if (dispatchRef.current.assignedDriverId !== driverId) break;

      const startNode = path[i];
      const endNode = path[i + 1];

      // Calculate how many sub-steps to take between these two nodes 
      // for a smooth 60fps-like animation. 
      // Overview paths can have nodes far apart.
      const dist = google.maps.geometry.spherical.computeDistanceBetween(startNode, endNode);
      const subSteps = Math.max(1, Math.floor(dist / 2)); // 1 step per 2 meters for ultra-smoothness
      const stepDuration = 120 / subSteps; // Distribute the 120ms total per segment

      for (let s = 1; s <= subSteps; s++) {
        const progress = s / subSteps;
        const lat = startNode.lat() + (endNode.lat() - startNode.lat()) * progress;
        const lng = startNode.lng() + (endNode.lng() - startNode.lng()) * progress;

        let heading = d.heading;
        if (progress < 1) {
          heading = getBearing(startNode.lat(), startNode.lng(), endNode.lat(), endNode.lng());
        }

        // Update ref directly
        d.lat = lat;
        d.lng = lng;
        d.heading = heading;
        d.speed_kmh = speed_kmh;
        if (d.ride) d.ride.status = status;

        // Update Marker
        if (d.marker) {
          d.marker.position = { lat: d.lat, lng: d.lng };
          const iconImg = (d.marker.content as Element)?.querySelector("img");
          if (iconImg) iconImg.style.transform = `rotate(${heading}deg)`;
        }

        // Update trail breadcrumbs (only every few steps for performance)
        if (s % 5 === 0 || s === subSteps) {
          d.trail.push(new google.maps.LatLng(d.lat, d.lng));
          if (d.trail.length > 50) d.trail.shift();
          if (d.trailPolyline) {
            d.trailPolyline.setPath(d.trail);
            d.trailPolyline.setVisible(showTrails && !!d.ride);
          }
        }

        // Throttle UI updates (list updates)
        if (s % 10 === 0) {
          setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
          if (selectedDriver?.driver_id === driverId) setSelectedDriver({ ...d });
        }

        await new Promise(r => setTimeout(r, Math.max(8, stepDuration)));
      }
    }
  }, [showTrails, selectedDriver]);

  /** FULL TRIP simulation: Driver -> Pickup -> Dropoff */
  const startDispatchTrip = useCallback(async () => {
    const cur = dispatchRef.current;
    if (!cur.assignedDriverId || !cur.pickup) return;

    const driverId = cur.assignedDriverId;
    const d = driversRef.current.get(driverId);
    if (!d || !d.ride) return;

    // Set to ongoing step to show progress UI
    setDispatch(prev => ({ ...prev, step: "ongoing" }));
    dispatchRef.current.step = "ongoing";

    const svc = new google.maps.DirectionsService();

    // PHASE 1: Move to Pickup
    const toPickup = await new Promise<google.maps.DirectionsResult | null>((resolve) => {
      svc.route({
        origin: { lat: d.lat, lng: d.lng },
        destination: cur.pickup!,
        travelMode: google.maps.TravelMode.DRIVING
      }, (res, status) => resolve(status === "OK" ? res : null));
    });

    if (toPickup?.routes[0] && dispatchRef.current.step === "ongoing") {
      await animateAlongPath(driverId, toPickup.routes[0].overview_path, "ARRIVING", 42);
    }

    if (dispatchRef.current.step !== "ongoing") return;

    // PHASE 2: Wait at Pickup
    d.ride.status = "ARRIVED";
    setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
    await new Promise(r => setTimeout(r, 2000));

    if (dispatchRef.current.step !== "ongoing") return;

    // PHASE 3: Move to Dropoff
    d.ride.status = "ONGOING";
    const toDropoff = await new Promise<google.maps.DirectionsResult | null>((resolve) => {
      svc.route({
        origin: cur.pickup!,
        destination: { lat: cur.pickup!.lat + 0.015, lng: cur.pickup!.lng + 0.02 },
        travelMode: google.maps.TravelMode.DRIVING
      }, (res, status) => resolve(status === "OK" ? res : null));
    });

    if (toDropoff?.routes[0] && dispatchRef.current.step === "ongoing") {
      await animateAlongPath(driverId, toDropoff.routes[0].overview_path, "ONGOING", 58);
    }

    if (dispatchRef.current.step !== "ongoing") return;

    // PHASE 4: Complete trip
    d.ride.status = "COMPLETED";
    setDispatch(prev => ({ ...prev, step: "assigned" }));
    dispatchRef.current.step = "assigned";
    setDriverList(Array.from(driversRef.current.values()).map(x => ({ ...x })));
  }, [animateAlongPath]);

  /** Reset dispatch to idle */
  const resetDispatch = useCallback(() => {
    clearDispatchOverlays();
    // Clear any mock rides from drivers
    driversRef.current.forEach(d => {
      if (d.ride && d.ride.id >= 77000) {
        d.ride = null;
      }
    });
    // Remove demo drivers if they were spawned
    if (demoActiveRef.current) {
      DEMO_IDS.forEach(id => {
        const d = driversRef.current.get(id);
        if (d) { d.marker.map = null; if (d.trailPolyline) d.trailPolyline.setMap(null); driversRef.current.delete(id); }
      });
      demoActiveRef.current = false;
      setDriverCount(driversRef.current.size);
      setDriverList(Array.from(driversRef.current.values()).map(d => ({ ...d })));
    }
    const idle: DispatchState = { step: "idle", pickup: null, nearbyDriverIds: [], notifiedDrivers: [], assignedDriverId: null, notifyCountdown: 8, radiusKm: DISPATCH_RADIUS_KM };
    setDispatch(idle);
    dispatchRef.current = idle;
  }, []);

  /** Seed 3 named demo drivers around the current map center */
  const seedDemoDrivers = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const center = map.getCenter()!;
    const baseLat = center.lat();
    const baseLng = center.lng();

    // 3 drivers at realistic offset positions within 1-2 km
    const demoConfigs = [
      { id: DEMO_IDS[0], name: "Ravi Kumar", dlat: 0.009, dlng: -0.006, heading: 135 },
      { id: DEMO_IDS[1], name: "Suresh Mani", dlat: -0.005, dlng: 0.011, heading: 45 },
      { id: DEMO_IDS[2], name: "Priya Sharma", dlat: 0.002, dlng: 0.014, heading: 200 },
    ];

    demoActiveRef.current = true;

    demoConfigs.forEach((cfg, i) => {
      setTimeout(() => {
        handlersRef.current.handleDriverUpdate({
          driver_id: cfg.id,
          name: cfg.name,
          lat: baseLat + cfg.dlat,
          lng: baseLng + cfg.dlng,
          status: "ONLINE",
          heading: cfg.heading,
          speed_kmh: 0,
          ts: Math.floor(Date.now() / 1000),
          ride: null,
        });
      }, i * 400); // stagger by 400ms each
    });
  }, []);

  /** Full demo: seed 3 drivers then run dispatch simulation */
  const startFullDemo = useCallback(() => {
    // Clear any existing demo
    if (demoActiveRef.current) {
      DEMO_IDS.forEach(id => {
        const d = driversRef.current.get(id);
        if (d) { d.marker.map = null; if (d.trailPolyline) d.trailPolyline.setMap(null); driversRef.current.delete(id); }
      });
      setDriverCount(driversRef.current.size);
      setDriverList(Array.from(driversRef.current.values()).map(d => ({ ...d })));
    }
    clearDispatchOverlays();
    setLeftTab("dispatch");

    // Show an interim "seeding" state
    const seedingState: DispatchState = {
      step: "idle", pickup: null, nearbyDriverIds: [], notifiedDrivers: [],
      assignedDriverId: null, notifyCountdown: 8, radiusKm: DISPATCH_RADIUS_KM,
    };
    setDispatch(seedingState);
    dispatchRef.current = seedingState;

    // Seed drivers, then fire dispatch after all 3 have appeared (3 × 400ms + 600ms buffer = 1800ms)
    seedDemoDrivers();
    setTimeout(() => {
      startDispatchSim();
    }, 1800);
  }, [seedDemoDrivers, startDispatchSim]);

  // ── Layer visibility sync ────────────────────────────────────────────────────
  useEffect(() => {
    driversRef.current.forEach(d => {
      // Only show trails if "showTrails" is ON AND the driver is actively on a ride
      // This prevents "laser beam" clutter from idle drivers
      const shouldShowTrail = showTrails && !!d.ride;

      if (d.rideGraphics) {
        d.rideGraphics.trailPolyline.setVisible(shouldShowTrail);
        d.rideGraphics.routePolyline.setVisible(showRoutes);
        d.rideGraphics.progressPolyline.setVisible(showRoutes);
      }
      if (d.trailPolyline) {
        d.trailPolyline.setVisible(shouldShowTrail);
        // If not on ride, clear the old trail points to prevent jumps on next ride
        if (!d.ride) d.trailPolyline.setPath([]);
      }
    });
    ridersRef.current.forEach(r => { r.marker.map = showRiders ? mapRef.current : null; });
  }, [showTrails, showRoutes, showRiders, driverList]);

  const filteredDrivers = driverList.filter(d => statusFilter === "ALL" || d.status === statusFilter || d.ride?.status === statusFilter);

  const S: Record<string, React.CSSProperties> = {
    root: { display: "flex", flexDirection: "column", height: "100vh", background: "#080808", fontFamily: "'Inter', 'SF Pro Display', sans-serif", color: "#e1e1e1", overflow: "hidden" },
    topbar: { display: "flex", alignItems: "center", justifyContent: "space-between", height: 52, padding: "0 20px", background: "#0d0d0d", borderBottom: "1px solid #1e1e1e", flexShrink: 0, zIndex: 20 },
    body: { flex: 1, display: "grid", gridTemplateColumns: "280px 1fr 340px", overflow: "hidden" },
    leftPanel: { background: "#0d0d0d", borderRight: "1px solid #1a1a1a", display: "flex", flexDirection: "column", overflow: "hidden" },
    rightPanel: { background: "#0d0d0d", borderLeft: "1px solid #1a1a1a", display: "flex", flexDirection: "column", overflow: "hidden" },
    mapWrap: { position: "relative", overflow: "hidden" },
  };

  const statuses = ["ALL", "ONLINE", "BUSY", "ASSIGNED", "ARRIVED", "ONGOING"];

  // ── Dispatch Panel (inline component) ────────────────────────────────────
  const DispatchPanel = () => {
    const stepLabels: Record<DispatchStep, string> = {
      idle: "IDLE", pickup_placed: "PICKUP PLACED", notifying: "NOTIFYING DRIVERS", assigned: "ASSIGNED", ongoing: "ONGOING",
    };
    const stepColors: Record<DispatchStep, string> = {
      idle: "#444", pickup_placed: "#3b82f6", notifying: "#f59e0b", assigned: "#22c55e", ongoing: "#ef4444",
    };
    const steps: DispatchStep[] = ["pickup_placed", "notifying", "assigned"];
    const stepIdx = steps.indexOf(dispatch.step);

    return (
      <div style={{ flex: 1, overflowY: "auto", padding: "14px 12px", display: "flex", flexDirection: "column", gap: 14 }} className="ds-fadein">
        {/* Step progress bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 4 }}>
          {steps.map((s, i) => (
            <div key={s} style={{ display: "flex", alignItems: "center", flex: 1 }}>
              <div style={{ width: 20, height: 20, borderRadius: "50%", background: stepIdx >= i ? stepColors[s] : "#1a1a1a", border: `2px solid ${stepIdx >= i ? stepColors[s] : "#2a2a2a"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 800, color: "#fff", flexShrink: 0, transition: "all 0.4s" }}>
                {stepIdx > i ? "✓" : i + 1}
              </div>
              {i < steps.length - 1 && <div style={{ flex: 1, height: 2, background: stepIdx > i ? stepColors[steps[i + 1]] : "#1e1e1e", margin: "0 2px", transition: "background 0.4s" }} />}
            </div>
          ))}
        </div>

        {/* Status badge */}
        <div style={{ background: `${stepColors[dispatch.step]}15`, border: `1px solid ${stepColors[dispatch.step]}44`, borderRadius: 10, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 800, color: stepColors[dispatch.step], letterSpacing: 0.5 }}>
            {stepLabels[dispatch.step]}
          </span>
          {dispatch.step === "notifying" && (
            <span style={{ fontSize: 10, fontWeight: 700, color: "#f59e0b", background: "rgba(245,158,11,0.12)", border: "1px solid #f59e0b44", borderRadius: 6, padding: "2px 8px" }}>
              ⏱ {dispatch.notifyCountdown}s
            </span>
          )}
          {dispatch.step === "assigned" && <span style={{ fontSize: 16 }}>✅</span>}
        </div>

        {/* Notified count */}
        {dispatch.step !== "idle" && (
          <div style={{ display: "flex", gap: 8 }}>
            {[{ label: "NEARBY", val: dispatch.nearbyDriverIds.length, color: "#3b82f6" },
            { label: "NOTIFIED", val: dispatch.notifiedDrivers.filter(d => d.status === "notified" || d.status === "accepted").length, color: "#f59e0b" },
            ...(dispatch.step === "assigned" ? [{ label: "ASSIGNED", val: 1, color: "#22c55e" }] : []),
            ].map(m => (
              <div key={m.label} style={{ flex: 1, background: "#111", border: "1px solid #1a1a1a", borderRadius: 8, padding: "8px 10px", textAlign: "center" }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: m.color }}>{m.val}</div>
                <div style={{ fontSize: 8, color: "#444", fontWeight: 700, letterSpacing: 0.5 }}>{m.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Driver list */}
        {dispatch.notifiedDrivers.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ fontSize: 9, fontWeight: 800, color: "#333", letterSpacing: 1 }}>ELIGIBLE DRIVERS</div>
            {dispatch.notifiedDrivers.map((nd, i) => {
              const statusColors = { waiting: "#4b5563", notified: "#f59e0b", accepted: "#22c55e", rejected: "#ef4444" };
              const statusIcons = { waiting: "⏳", notified: "🔔", accepted: "✅", rejected: "❌" };
              const sc = statusColors[nd.status];
              return (
                <div key={nd.driver_id} className="ds-slideup" style={{ animationDelay: `${i * 0.08}s`, background: nd.status === "accepted" ? "rgba(34,197,94,0.06)" : nd.status === "rejected" ? "rgba(239,68,68,0.04)" : "#111", border: `1px solid ${sc}33`, borderRadius: 10, padding: "10px 12px", opacity: nd.status === "rejected" ? 0.55 : 1, transition: "all 0.3s" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ fontSize: 8, fontWeight: 800, color: "#444" }}>#{i + 1}</div>
                      <span style={{ fontSize: 12, fontWeight: 700, color: nd.status === "accepted" ? "#22c55e" : "#ccc" }}>{nd.name}</span>
                    </div>
                    <span style={{ fontSize: 12 }}>{statusIcons[nd.status]}</span>
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <span style={{ fontSize: 10, color: "#555" }}>📍 {nd.dist_km} km away</span>
                    <span style={{ fontSize: 10, color: "#555" }}>⏱ ~{nd.eta_min} min ETA</span>
                  </div>
                  <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: sc }} />
                    <span style={{ fontSize: 9, fontWeight: 700, color: sc, textTransform: "uppercase" }}>{nd.status}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Control buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
          {dispatch.step === "idle" && (
            <>
              {/* PRIMARY: Full demo with 3 drivers */}
              <button onClick={startFullDemo}
                style={{ padding: "13px 0", borderRadius: 10, border: "1px solid #22c55e55", background: "rgba(34,197,94,0.1)", color: "#22c55e", fontSize: 12, fontWeight: 800, cursor: "pointer", letterSpacing: 0.5, transition: "all 0.2s", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(34,197,94,0.2)"}
                onMouseLeave={e => e.currentTarget.style.background = "rgba(34,197,94,0.1)"}>
                <span style={{ fontSize: 16 }}>🎬</span> FULL DEMO (3 Drivers)
              </button>
              {/* SECONDARY: Use existing real drivers */}
              <button onClick={startDispatchSim}
                style={{ padding: "9px 0", borderRadius: 10, border: "1px solid #3b82f633", background: "transparent", color: "#3b82f6", fontSize: 10, fontWeight: 700, cursor: "pointer", letterSpacing: 0.5, transition: "all 0.2s", opacity: 0.7 }}
                onMouseEnter={e => { e.currentTarget.style.opacity = "1"; e.currentTarget.style.borderColor = "#3b82f6"; }}
                onMouseLeave={e => { e.currentTarget.style.opacity = "0.7"; e.currentTarget.style.borderColor = "#3b82f633"; }}>
                ▶ Use Real Drivers Only
              </button>
            </>
          )}
          {dispatch.step === "notifying" && (
            <button onClick={assignDriver}
              style={{ padding: "11px 0", borderRadius: 10, border: "1px solid #22c55e55", background: "rgba(34,197,94,0.12)", color: "#22c55e", fontSize: 11, fontWeight: 800, cursor: "pointer", letterSpacing: 0.5, transition: "all 0.2s" }}
              onMouseEnter={e => e.currentTarget.style.background = "rgba(34,197,94,0.2)"}
              onMouseLeave={e => e.currentTarget.style.background = "rgba(34,197,94,0.12)"}>
              ⚡ FORCE ASSIGN NOW
            </button>
          )}
          {dispatch.step === "assigned" && (
            <button onClick={startDispatchTrip}
              style={{ padding: "13px 0", borderRadius: 10, border: "2px solid #22c55e", background: "#22c55e", color: "#fff", fontSize: 12, fontWeight: 900, cursor: "pointer", letterSpacing: 0.5, transition: "all 0.2s", boxShadow: "0 0 20px rgba(34,197,94,0.4)" }}
              onMouseEnter={e => e.currentTarget.style.transform = "scale(1.02)"}
              onMouseLeave={e => e.currentTarget.style.transform = "scale(1)"}>
              🚀 START TRIP (TRACKING)
            </button>
          )}
          {dispatch.step === "ongoing" && (
            <div style={{ padding: "12px", borderRadius: 10, background: "rgba(34,197,94,0.1)", border: "1px solid #22c55e44", color: "#22c55e", fontSize: 11, fontWeight: 700, textAlign: "center" }}>
              🕒 TRIP IN PROGRESS...
            </div>
          )}
          {dispatch.step !== "idle" && (
            <button onClick={resetDispatch}
              style={{ padding: "9px 0", borderRadius: 10, border: "1px solid #2a2a2a", background: "transparent", color: "#555", fontSize: 10, fontWeight: 700, cursor: "pointer", letterSpacing: 0.5, transition: "all 0.2s" }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "#ef4444"; e.currentTarget.style.color = "#ef4444"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "#2a2a2a"; e.currentTarget.style.color = "#555"; }}>
              ✕ RESET SIMULATION
            </button>
          )}
        </div>

        {/* Hint */}
        {dispatch.step === "idle" && (
          <div style={{ textAlign: "center", color: "#2a2a2a", fontSize: 10, lineHeight: 1.8, marginTop: 4 }}>
            <span style={{ color: "#22c55e66", fontWeight: 700 }}>FULL DEMO</span> spawns 3 demo drivers,<br />
            places a pickup, notifies all &amp; assigns nearest.
          </div>
        )}
      </div>
    );
  };

  const Dot = ({ color, pulse }: { color: string; pulse?: boolean }) => (
    <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0, boxShadow: pulse ? `0 0 6px ${color}` : "none" }} />
  );

  const onDriverClick = (d: DriverPing) => {
    setSelectedDriver(driversRef.current.get(d.driver_id) || d);
    mapRef.current?.panTo({ lat: d.lat, lng: d.lng });
    mapRef.current?.setZoom(15);
  };

  if (!isLoaded) return <div style={{ display: "flex", height: "100%", alignItems: "center", justifyContent: "center", background: "#080808", color: "#fff", fontSize: 13, letterSpacing: 2 }}>INITIALIZING MAP...</div>;

  return (
    <>
      <div style={S.root}>
        {/* ── TOP BAR ──────────────────────────────────────────────────── */}
        <div style={S.topbar}>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: "#1a1a2e", border: "1px solid #3b82f6", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>🗺</div>
              <span style={{ fontWeight: 800, fontSize: 14, letterSpacing: -0.3 }}>FleetOps</span>
              <span style={{ color: "#333", fontSize: 14 }}>|</span>
              <span style={{ color: "#555", fontSize: 11, fontWeight: 600 }}>Live Operations Center</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: wsStatus === "connected" ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)", border: `1px solid ${wsStatus === "connected" ? "#1a3a1a" : "#3a1a1a"}`, borderRadius: 20, padding: "3px 10px" }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: wsStatus === "connected" ? "#22c55e" : "#ef4444", boxShadow: wsStatus === "connected" ? "0 0 8px #22c55e" : "none" }} />
              <span style={{ fontSize: 10, fontWeight: 700, color: wsStatus === "connected" ? "#22c55e" : "#ef4444" }}>{wsStatus === "connected" ? "LIVE" : wsStatus === "connecting" ? "CONNECTING" : "OFFLINE"}</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {[{ label: "DRIVERS", value: driverCount, color: "#3b82f6" }, { label: "RIDERS", value: riderCount, color: "#8b5cf6" }, { label: "ALERTS", value: incidents.length, color: incidents.length > 0 ? "#ef4444" : "#333" }].map(s => (
              <div key={s.label} style={{ background: "#111", border: "1px solid #1e1e1e", borderRadius: 8, padding: "4px 14px", textAlign: "center", minWidth: 64 }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: s.color, lineHeight: 1.2 }}>{s.value}</div>
                <div style={{ fontSize: 8, fontWeight: 700, color: "#444", letterSpacing: 1 }}>{s.label}</div>
              </div>
            ))}
          </div>
          <button onClick={clearAllMapData} style={{ background: "transparent", border: "1px solid #2a2a2a", color: "#555", fontSize: 10, padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontWeight: 700, letterSpacing: 0.5, transition: "all 0.15s" }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "#ef4444"; e.currentTarget.style.color = "#ef4444"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "#2a2a2a"; e.currentTarget.style.color = "#555"; }}>
            CLEAR ALL
          </button>
        </div>

        <div style={S.body}>
          {/* ── LEFT PANEL ───────────────────────────────────────────────── */}
          <div style={S.leftPanel}>
            {/* Tab switcher */}
            <div style={{ display: "flex", borderBottom: "1px solid #1a1a1a" }}>
              {(["drivers", "riders", "incidents", "dispatch"] as const).map(tab => {
                const tabColor = tab === "dispatch" ? "#3b82f6" : tab === "riders" ? "#8b5cf6" : "#3b82f6";
                const isActive = leftTab === tab;
                const hasBadge = tab === "dispatch" && dispatch.step !== "idle";
                return (
                  <button key={tab} onClick={() => setLeftTab(tab)}
                    style={{ flex: 1, padding: "11px 0", background: hasBadge ? "rgba(59,130,246,0.06)" : "transparent", border: "none", borderBottom: isActive ? `2px solid ${tabColor}` : "2px solid transparent", color: isActive ? "#fff" : hasBadge ? "#3b82f6" : "#444", fontSize: 9, fontWeight: 700, letterSpacing: 0.5, cursor: "pointer", textTransform: "uppercase", transition: "color 0.15s", position: "relative" }}>
                    {tab === "drivers" ? `Drivers (${filteredDrivers.length})` : tab === "riders" ? `Riders (${riderList.length})` : tab === "incidents" ? `Alerts (${incidents.length})` : "Dispatch"}
                    {hasBadge && <span style={{ position: "absolute", top: 5, right: 4, width: 6, height: 6, borderRadius: "50%", background: "#3b82f6", boxShadow: "0 0 6px #3b82f6" }} />}
                  </button>
                );
              })}
            </div>

            {leftTab === "drivers" && (
              <>
                {/* Status filter pills */}
                <div style={{ padding: "10px 10px 8px", borderBottom: "1px solid #141414", display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {statuses.map(s => (
                    <button key={s} onClick={() => setStatusFilter(s)}
                      style={{ padding: "3px 9px", borderRadius: 20, border: `1px solid ${statusFilter === s ? (STATUS_COLOR[s] || "#3b82f6") : "#222"}`, background: statusFilter === s ? `${STATUS_COLOR[s] || "#3b82f6"}18` : "transparent", color: statusFilter === s ? (STATUS_COLOR[s] || "#3b82f6") : "#444", fontSize: 9, fontWeight: 700, cursor: "pointer", transition: "all 0.15s", letterSpacing: 0.5 }}>
                      {s}
                    </button>
                  ))}
                </div>
                {/* Driver list */}
                <div style={{ flex: 1, overflowY: "auto" }}>
                  {filteredDrivers.length === 0 ? (
                    <div style={{ color: "#2a2a2a", fontSize: 11, textAlign: "center", marginTop: 48, fontWeight: 600 }}>No drivers online</div>
                  ) : filteredDrivers.sort((a, b) => (b.ride ? 1 : 0) - (a.ride ? 1 : 0)).map(d => {
                    const isSelected = selectedDriver?.driver_id === d.driver_id;
                    const hasAlert = deviationAlerts.has(d.driver_id);
                    const sc = STATUS_COLOR[d.ride?.status || d.status] ?? "#4b5563";
                    return (
                      <div key={d.driver_id} onClick={() => onDriverClick(d)}
                        style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderBottom: "1px solid #111", cursor: "pointer", background: isSelected ? "#0f1829" : "transparent", borderLeft: isSelected ? "3px solid #3b82f6" : "3px solid transparent", transition: "background 0.15s" }}
                        onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "#111"; }}
                        onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}>
                        <div style={{ position: "relative", flexShrink: 0 }}>
                          <div style={{ width: 36, height: 36, borderRadius: "50%", background: "#141414", border: `2px solid ${sc}`, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                            <img src={VEHICLE_ICONS[d.ride?.vehicle_type || "go"]} style={{ width: 24, height: 24, objectFit: "contain" }} />
                          </div>
                          {hasAlert && <div style={{ position: "absolute", top: -2, right: -2, width: 10, height: 10, borderRadius: "50%", background: "#ef4444", border: "2px solid #0d0d0d" }} />}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: isSelected ? "#fff" : "#ccc", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.name || `Driver #${d.driver_id}`}</span>
                            <div style={{ display: "flex", alignItems: "center", gap: 4, flexShrink: 0, marginLeft: 6 }}>
                              <Dot color={sc} pulse={!!d.ride} />
                              <span style={{ fontSize: 9, fontWeight: 700, color: sc }}>{d.ride?.status || d.status}</span>
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            {d.speed_kmh != null && <span style={{ fontSize: 10, color: "#555" }}>🚗 {d.speed_kmh.toFixed(0)} km/h</span>}
                            {d.eta != null && <span style={{ fontSize: 10, color: "#555" }}>⏱ {d.eta}min ETA</span>}
                            {d.ride && <span style={{ fontSize: 10, color: "#3b82f630" }}>#{d.ride.id}</span>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            {leftTab === "riders" && (
              <div style={{ flex: 1, overflowY: "auto" }}>
                {riderList.length === 0 ? (
                  <div style={{ color: "#2a2a2a", fontSize: 11, textAlign: "center", marginTop: 48, fontWeight: 600 }}>No riders active</div>
                ) : riderList.map(r => {
                  const sc = STATUS_COLOR[r.status || "WAITING"] ?? "#8b5cf6";
                  return (
                    <div key={r.rider_id} onClick={() => mapRef.current?.panTo({ lat: r.lat, lng: r.lng })}
                      style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 12px", borderBottom: "1px solid #111", cursor: "pointer" }}
                      onMouseEnter={e => e.currentTarget.style.background = "#141414"}
                      onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                      <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#1a1a1a", border: `2px solid ${sc}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>👤</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: "#fff" }}>{r.rider_name || `Rider #${r.rider_id}`}</span>
                          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <Dot color={sc} pulse={r.status === "SEARCHING"} />
                            <span style={{ fontSize: 9, fontWeight: 700, color: sc }}>{r.status || "WAITING"}</span>
                          </div>
                        </div>
                        <div style={{ fontSize: 10, color: "#555", marginTop: 2 }}>Ride #{r.ride_id}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {leftTab === "dispatch" && <DispatchPanel />}

            {leftTab === "incidents" && (
              <div style={{ flex: 1, overflowY: "auto" }}>
                <div style={{ display: "flex", justifyContent: "flex-end", padding: "8px 10px", borderBottom: "1px solid #141414" }}>
                  {incidents.length > 0 && <button onClick={() => setIncidents([])} style={{ background: "transparent", border: "1px solid #222", color: "#555", fontSize: 9, padding: "4px 10px", borderRadius: 4, cursor: "pointer", fontWeight: 700 }}>CLEAR ALL</button>}
                </div>
                {incidents.length === 0 ? (
                  <div style={{ color: "#2a2a2a", fontSize: 11, textAlign: "center", marginTop: 48, fontWeight: 600 }}>No recent incidents</div>
                ) : incidents.map(inc => (
                  <div key={inc.id} onClick={() => { const d = driversRef.current.get(inc.driver_id); if (d) { setSelectedDriver(d); mapRef.current?.panTo({ lat: d.lat, lng: d.lng }); } }}
                    style={{ padding: "10px 12px", borderBottom: "1px solid #111", cursor: "pointer" }}
                    onMouseEnter={e => e.currentTarget.style.background = "#141414"}
                    onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 9, fontWeight: 800, color: "#ef4444", letterSpacing: 1 }}>⚠ {inc.type}</span>
                      <span style={{ fontSize: 9, color: "#333" }}>{new Date(inc.ts * 1000).toLocaleTimeString()}</span>
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#ccc", marginBottom: 2 }}>{inc.driver_name}</div>
                    <div style={{ fontSize: 11, color: "#555" }}>{inc.msg}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Legend */}
            <div style={{ borderTop: "1px solid #141414", padding: "10px 12px", display: "flex", flexWrap: "wrap", gap: 8 }}>
              {Object.entries(STATUS_COLOR).map(([s, c]) => (
                <div key={s} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: c }} />
                  <span style={{ fontSize: 9, color: "#444", fontWeight: 600 }}>{s}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── MAP CENTER ───────────────────────────────────────────────── */}
          <div style={S.mapWrap}>
            <GoogleMap
              onLoad={m => {
                mapRef.current = m;
                mapReadyRef.current = true;
                flushPending();
              }}
              center={DEFAULT_CENTER}
              zoom={12}
              mapContainerStyle={MAP_CONTAINER}
              options={{ mapId: "ac584fdc61f9c23a0aecc050", disableDefaultUI: true, zoomControl: true }}
            />
            {/* Floating layer toggles */}
            <div style={{ position: "absolute", bottom: 24, left: 16, display: "flex", flexDirection: "column", gap: 6 }}>
              {[{ label: "Routes", key: "routes", val: showRoutes, set: setShowRoutes, color: "#3b82f6" },
              { label: "Trails", key: "trails", val: showTrails, set: setShowTrails, color: "#22d3ee" },
              { label: "Riders", key: "riders", val: showRiders, set: setShowRiders, color: "#8b5cf6" }].map(l => (
                <button key={l.key} onClick={() => l.set(!l.val)}
                  style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 12px", borderRadius: 8, border: `1px solid ${l.val ? l.color + "55" : "#2a2a2a"}`, background: l.val ? l.color + "15" : "rgba(10,10,10,0.85)", color: l.val ? l.color : "#444", fontSize: 10, fontWeight: 700, cursor: "pointer", backdropFilter: "blur(6px)", letterSpacing: 0.5 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: l.val ? l.color : "#333" }} />
                  {l.label}
                </button>
              ))}
            </div>

            {/* Floating dispatch button (bottom-right) */}
            <div style={{ position: "absolute", bottom: 24, right: 16, display: "flex", flexDirection: "column", gap: 6 }}>
              {dispatch.step === "idle" ? (
                <button onClick={() => { setLeftTab("dispatch"); startDispatchSim(); }}
                  className="ds-fadein"
                  style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 16px", borderRadius: 10, border: "1px solid #3b82f655", background: "rgba(10,10,10,0.9)", color: "#3b82f6", fontSize: 11, fontWeight: 800, cursor: "pointer", backdropFilter: "blur(8px)", letterSpacing: 0.5, boxShadow: "0 4px 20px rgba(0,0,0,0.5)" }}
                  onMouseEnter={e => { e.currentTarget.style.background = "rgba(59,130,246,0.15)"; e.currentTarget.style.borderColor = "#3b82f6"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = "rgba(10,10,10,0.9)"; e.currentTarget.style.borderColor = "#3b82f655"; }}>
                  <span style={{ fontSize: 14 }}>📡</span> SIMULATE DISPATCH
                </button>
              ) : (
                <button onClick={resetDispatch}
                  style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 16px", borderRadius: 10, border: "1px solid #ef444455", background: "rgba(10,10,10,0.9)", color: "#ef4444", fontSize: 11, fontWeight: 800, cursor: "pointer", backdropFilter: "blur(8px)", letterSpacing: 0.5 }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(239,68,68,0.1)"}
                  onMouseLeave={e => e.currentTarget.style.background = "rgba(10,10,10,0.9)"}>
                  ✕ END SIM
                </button>
              )}
            </div>

            {/* Dispatch status overlay banner */}
            {dispatch.step !== "idle" && (
              <div className="ds-slideup" style={{ position: "absolute", top: 12, right: 16, background: "rgba(8,8,8,0.9)", border: `1px solid ${dispatch.step === "ongoing" ? "#ef444444" : dispatch.step === "assigned" ? "#22c55e44" : dispatch.step === "notifying" ? "#f59e0b44" : "#3b82f644"}`, borderRadius: 12, padding: "10px 14px", backdropFilter: "blur(10px)", minWidth: 190, boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: dispatch.step === "ongoing" ? "#ef4444" : dispatch.step === "assigned" ? "#22c55e" : dispatch.step === "notifying" ? "#f59e0b" : "#3b82f6", boxShadow: `0 0 8px ${dispatch.step === "ongoing" ? "#ef4444" : dispatch.step === "assigned" ? "#22c55e" : dispatch.step === "notifying" ? "#f59e0b" : "#3b82f6"}` }} />
                  <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: 0.5, color: dispatch.step === "ongoing" ? "#ef4444" : dispatch.step === "assigned" ? "#22c55e" : dispatch.step === "notifying" ? "#f59e0b" : "#3b82f6" }}>
                    {dispatch.step === "pickup_placed" && "📍 PICKUP PLACED"}
                    {dispatch.step === "notifying" && `🔔 NOTIFYING — ${dispatch.notifyCountdown}s`}
                    {dispatch.step === "assigned" && "✅ DRIVER ASSIGNED"}
                    {dispatch.step === "ongoing" && "🚗 TRIP ONGOING"}
                  </span>
                </div>
                {dispatch.step !== "assigned" && (
                  <div style={{ fontSize: 10, color: "#555" }}>Notified: <span style={{ color: "#f59e0b", fontWeight: 700 }}>{dispatch.notifiedDrivers.filter(d => d.status === "notified").length} driver{dispatch.notifiedDrivers.length !== 1 ? "s" : ""}</span></div>
                )}
                {dispatch.step === "assigned" && dispatch.notifiedDrivers[0] && (
                  <div style={{ fontSize: 10, color: "#555" }}>Assigned: <span style={{ color: "#22c55e", fontWeight: 700 }}>{dispatch.notifiedDrivers.find(d => d.status === "accepted")?.name}</span></div>
                )}
                {dispatch.step === "notifying" && (
                  <>
                    <div style={{ marginTop: 6, height: 3, background: "#1a1a1a", borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ height: "100%", background: "#f59e0b", borderRadius: 2, width: `${(dispatch.notifyCountdown / 8) * 100}%`, transition: "width 1s linear" }} />
                    </div>
                    <button onClick={assignDriver} style={{ marginTop: 8, width: "100%", padding: "6px 0", borderRadius: 6, border: "1px solid #22c55e55", background: "rgba(34,197,94,0.1)", color: "#22c55e", fontSize: 9, fontWeight: 800, cursor: "pointer", letterSpacing: 0.5 }}
                      onMouseEnter={e => e.currentTarget.style.background = "rgba(34,197,94,0.2)"}
                      onMouseLeave={e => e.currentTarget.style.background = "rgba(34,197,94,0.1)"}>
                      ⚡ ASSIGN NOW
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Zoom hint */}
            <div style={{ position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)", background: "rgba(10,10,10,0.8)", border: "1px solid #1e1e1e", borderRadius: 20, padding: "4px 14px", display: "flex", alignItems: "center", gap: 8, backdropFilter: "blur(6px)" }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: wsStatus === "connected" ? "#22c55e" : "#ef4444", boxShadow: wsStatus === "connected" ? "0 0 8px #22c55e" : "none" }} />
              <span style={{ fontSize: 10, fontWeight: 700, color: "#555" }}>{driverCount} driver{driverCount !== 1 ? "s" : ""} · {riderCount} rider{riderCount !== 1 ? "s" : ""} tracked</span>
            </div>
          </div>

          {/* ── RIGHT PANEL (Detail) ──────────────────────────────────────── */}
          <div style={S.rightPanel}>
            {selectedDriver ? (
              <>
                <div style={{ padding: "14px 16px", borderBottom: "1px solid #1a1a1a", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#444", letterSpacing: 1 }}>DRIVER DETAIL</span>
                  <button onClick={() => setSelectedDriver(null)} style={{ background: "none", border: "none", color: "#444", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>✕</button>
                </div>
                <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
                  {/* Driver header */}
                  <div style={{ display: "flex", gap: 14, marginBottom: 20, alignItems: "center" }}>
                    <div style={{ position: "relative" }}>
                      <div style={{ width: 56, height: 56, borderRadius: 12, background: "#111", border: `2px solid ${STATUS_COLOR[selectedDriver.status] || "#333"}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <img src={VEHICLE_ICONS[selectedDriver.ride?.vehicle_type || "go"]} style={{ width: 38, height: 38, objectFit: "contain" }} />
                      </div>
                      {deviationAlerts.has(selectedDriver.driver_id) && (
                        <div style={{ position: "absolute", top: -4, right: -4, width: 18, height: 18, borderRadius: "50%", background: "#ef4444", border: "2px solid #0d0d0d", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9 }}>⚠</div>
                      )}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "#fff", marginBottom: 4 }}>{selectedDriver.name || `Driver #${selectedDriver.driver_id}`}</div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                        <Dot color={STATUS_COLOR[selectedDriver.status] || "#555"} pulse />
                        <span style={{ fontSize: 11, fontWeight: 700, color: STATUS_COLOR[selectedDriver.status] || "#555" }}>{selectedDriver.status}</span>
                      </div>
                      <div style={{ fontSize: 11, color: "#444" }}>#{selectedDriver.driver_id} · {selectedDriver.phone || "—"}</div>
                    </div>
                  </div>

                  {/* Live metrics grid */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                    {[{ label: "SPEED", value: selectedDriver.speed_kmh != null ? `${selectedDriver.speed_kmh.toFixed(0)} km/h` : "—", color: (selectedDriver.speed_kmh ?? 0) > 80 ? "#ef4444" : "#fff", sub: (selectedDriver.speed_kmh ?? 0) > 80 ? "⚠ OVERSPEEDING" : " " },
                    { label: "ETA", value: selectedDriver.eta != null ? `${selectedDriver.eta} min` : "—", color: "#fff", sub: " " },
                    { label: "LATENCY", value: selectedDriver.latency_ms != null ? `${selectedDriver.latency_ms}ms` : "—", color: (selectedDriver.latency_ms ?? 0) > 2000 ? "#ef4444" : "#22c55e", sub: (selectedDriver.latency_ms ?? 0) > 2000 ? "HIGH LATENCY" : "GOOD" },
                    { label: "PING", value: selectedDriver.interval_s ? `${selectedDriver.interval_s}s` : "Live", color: "#3b82f6", sub: " " },
                    ].map(m => (
                      <div key={m.label} style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 10, padding: "10px 12px" }}>
                        <div style={{ fontSize: 8, fontWeight: 800, color: "#333", letterSpacing: 1, marginBottom: 4 }}>{m.label}</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: m.color }}>{m.value}</div>
                        <div style={{ fontSize: 8, color: "#333", marginTop: 2 }}>{m.sub}</div>
                      </div>
                    ))}
                  </div>

                  {/* Deviation alert */}
                  {deviationAlerts.has(selectedDriver.driver_id) && (
                    <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "12px 14px", marginBottom: 14, display: "flex", gap: 10, alignItems: "flex-start" }}>
                      <span style={{ fontSize: 16 }}>🚨</span>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "#ef4444", marginBottom: 2 }}>Route Deviation</div>
                        <div style={{ fontSize: 11, color: "#f87171" }}>{deviationAlerts.get(selectedDriver.driver_id)?.deviation_m}m off planned route</div>
                      </div>
                    </div>
                  )}

                  {/* Ride info */}
                  {selectedDriver.ride ? (
                    <div style={{ background: "#111", border: "1px solid #1a1a1a", borderRadius: 12, overflow: "hidden" }}>
                      <div style={{ padding: "10px 14px", background: "#0f1829", borderBottom: "1px solid #1a1a1a", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 10, fontWeight: 800, color: "#3b82f6" }}>RIDE #{selectedDriver.ride.id}</span>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <Dot color={STATUS_COLOR[selectedDriver.ride.status] || "#555"} pulse />
                          <span style={{ fontSize: 10, fontWeight: 700, color: STATUS_COLOR[selectedDriver.ride.status] || "#555" }}>{selectedDriver.ride.status}</span>
                        </div>
                      </div>
                      <div style={{ padding: "12px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid #191919" }}>
                          <div style={{ width: 30, height: 30, borderRadius: 8, background: "#1a1a2e", border: "1px solid #2a2a4e", display: "flex", alignItems: "center", justifyContent: "center" }}>👤</div>
                          <div>
                            <div style={{ fontSize: 12, fontWeight: 700, color: "#ccc" }}>{selectedDriver.ride.rider_name || "Guest Rider"}</div>
                            <div style={{ fontSize: 10, color: "#444" }}>Rider #{selectedDriver.ride.rider_id}</div>
                          </div>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", marginTop: 3, flexShrink: 0 }} />
                            <div>
                              <div style={{ fontSize: 9, color: "#444", fontWeight: 700, letterSpacing: 1, marginBottom: 2 }}>PICKUP</div>
                              <div style={{ fontSize: 11, color: "#aaa", lineHeight: 1.4 }}>{selectedDriver.ride.pickup_address || `${selectedDriver.ride.pickup.lat.toFixed(4)}, ${selectedDriver.ride.pickup.lng.toFixed(4)}`}</div>
                            </div>
                          </div>
                          <div style={{ marginLeft: 4, width: 0, borderLeft: "1px dashed #2a2a2a", height: 14 }} />
                          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", marginTop: 3, flexShrink: 0 }} />
                            <div>
                              <div style={{ fontSize: 9, color: "#444", fontWeight: 700, letterSpacing: 1, marginBottom: 2 }}>DROPOFF</div>
                              <div style={{ fontSize: 11, color: "#aaa", lineHeight: 1.4 }}>{selectedDriver.ride.drop_address || `${selectedDriver.ride.dropoff.lat.toFixed(4)}, ${selectedDriver.ride.dropoff.lng.toFixed(4)}`}</div>
                            </div>
                          </div>
                        </div>
                        {selectedDriver.ride.status === "ONGOING" && selectedDriver.ride.distance_km != null && (
                          <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #191919", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontSize: 10, color: "#444", fontWeight: 700 }}>DISTANCE COVERED</span>
                            <span style={{ fontSize: 15, fontWeight: 800, color: "#22c55e" }}>{selectedDriver.ride.distance_km.toFixed(2)} <span style={{ fontSize: 10, color: "#3a7a3a" }}>km</span></span>
                          </div>
                        )}
                      </div>

                      {/* ── Admin Actions ── */}
                      <div style={{ padding: "12px 14px", borderTop: "1px solid #1a1a1a" }}>
                        <div style={{ fontSize: 9, fontWeight: 800, color: "#333", letterSpacing: 1, marginBottom: 10 }}>ADMIN ACTIONS</div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {["ASSIGNED", "ARRIVED", "ONGOING", "OFFERED", "SEARCHING"].includes(selectedDriver.ride.status) && (
                            <button
                              onClick={() => setShowResolution(true)}
                              style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444", fontSize: 11, fontWeight: 700, cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}
                              onMouseEnter={e => e.currentTarget.style.background = "rgba(239,68,68,0.15)"}
                              onMouseLeave={e => e.currentTarget.style.background = "rgba(239,68,68,0.08)"}
                            >
                              ⚠️ Resolve & Cancel
                            </button>
                          )}
                          {["ASSIGNED", "ARRIVED", "OFFERED"].includes(selectedDriver.ride.status) && (
                            <button
                              onClick={() => setRideAction({ action: "reassign", rideId: selectedDriver.ride!.id, label: "Reassign to a new driver?" })}
                              style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b", fontSize: 11, fontWeight: 700, cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}
                              onMouseEnter={e => e.currentTarget.style.background = "rgba(245,158,11,0.15)"}
                              onMouseLeave={e => e.currentTarget.style.background = "rgba(245,158,11,0.08)"}
                            >
                              🔄 Reassign Driver
                            </button>
                          )}
                          {["COMPLETED"].includes(selectedDriver.ride.status) && (
                            <button
                              onClick={() => setShowResolution(true)}
                              style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.3)", color: "#3b82f6", fontSize: 11, fontWeight: 700, cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}
                              onMouseEnter={e => e.currentTarget.style.background = "rgba(59,130,246,0.15)"}
                              onMouseLeave={e => e.currentTarget.style.background = "rgba(59,130,246,0.08)"}
                            >
                              💸 Resolve & Refund
                            </button>
                          )}
                        </div>
                        {/* Action result toast */}
                        {rideActionResult && (
                          <div style={{ marginTop: 10, padding: "8px 12px", borderRadius: 8, background: rideActionResult.ok ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)", border: `1px solid ${rideActionResult.ok ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`, fontSize: 11, fontWeight: 600, color: rideActionResult.ok ? "#22c55e" : "#ef4444" }}>
                            {rideActionResult.ok ? "✓" : "✗"} {rideActionResult.msg}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div style={{ textAlign: "center", padding: "40px 20px", color: "#2a2a2a" }}>
                      <div style={{ fontSize: 36, marginBottom: 10 }}>🚗</div>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>No active ride</div>
                      <div style={{ fontSize: 10, marginTop: 4 }}>Awaiting dispatch</div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "#222", padding: 24 }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>👆</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#333", marginBottom: 6 }}>Select a Driver</div>
                <div style={{ fontSize: 11, color: "#222", textAlign: "center", lineHeight: 1.6 }}>Click any driver on the map or in the left panel to view real-time details</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Admin Action Confirm Modal ── */}
      {rideAction && (
        <div
          onClick={() => !rideActionLoading && setRideAction(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)", zIndex: 5000, display: "flex", alignItems: "center", justifyContent: "center" }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{ background: "#0f0f0f", border: "1px solid #2a2a2a", borderRadius: 16, padding: "28px 32px", minWidth: 320, boxShadow: "0 24px 80px rgba(0,0,0,0.8)" }}
          >
            <div style={{ fontSize: 32, marginBottom: 16, textAlign: "center" }}>
              {rideAction?.action === "cancel" ? "🚫" : rideAction?.action === "reassign" ? "🔄" : "💸"}
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#fff", textAlign: "center", marginBottom: 8 }}>
              {rideAction?.label}
            </div>
            <div style={{ fontSize: 12, color: "#555", textAlign: "center", marginBottom: 24 }}>
              Ride #{rideAction?.rideId} · This action cannot be undone.
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => setRideAction(null)}
                disabled={rideActionLoading}
                style={{ flex: 1, padding: "10px 0", borderRadius: 8, background: "#1a1a1a", border: "1px solid #2a2a2a", color: "#aaa", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                disabled={rideActionLoading}
                onClick={async () => {
                  if (!rideAction) return;
                  const { action, rideId } = rideAction;
                  setRideActionLoading(true);
                  try {
                    const { api } = await import("../services/api");
                    await api.post("/rides/admin/rides/actions/", {
                      ride_id: rideId,
                      action: action,
                    });
                    setRideActionResult({ ok: true, msg: `${action.charAt(0).toUpperCase() + action.slice(1)} successful!` });
                    setRideAction(null);
                    setTimeout(() => setRideActionResult(null), 4000);
                  } catch (err: any) {
                    const detail = err?.response?.data?.error || "Action failed. Try again.";
                    setRideActionResult({ ok: false, msg: detail });
                    setRideAction(null);
                    setTimeout(() => setRideActionResult(null), 5000);
                  } finally {
                    setRideActionLoading(false);
                  }
                }}
                style={{
                  flex: 1, padding: "10px 0", borderRadius: 8, border: "none",
                  background: rideAction?.action === "cancel" ? "#ef4444" : rideAction?.action === "reassign" ? "#f59e0b" : "#3b82f6",
                  color: "#fff", fontSize: 12, fontWeight: 700, cursor: rideActionLoading ? "not-allowed" : "pointer",
                  opacity: rideActionLoading ? 0.6 : 1,
                }}
              >
                {rideActionLoading ? "Processing…" : `Confirm ${rideAction?.action.charAt(0).toUpperCase() + rideAction?.action.slice(1)}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {showResolution && selectedDriver?.ride && (
        <ResolutionModal
          ride={selectedDriver.ride}
          onClose={() => setShowResolution(false)}
          onSubmit={handleResolutionSubmit}
        />
      )}
    </>
  );
}
