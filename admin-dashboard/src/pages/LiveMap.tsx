import { useEffect, useRef } from "react";
import { api } from "../services/api";

declare var google: any;

export default function LiveMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);

  // Store active markers to clear them on update
  const markersRef = useRef<any[]>([]);

  // Helper to create marker
  const createDriverMarker = (d: any) => {
    if (!mapInstance.current) return;

    const el = document.createElement("div");
    el.style.width = "14px";
    el.style.height = "14px";
    el.style.borderRadius = "50%";
    el.style.background = "#2ecc71"; // Green
    el.style.border = "2px solid white";
    el.style.boxShadow = "0 0 6px rgba(0,0,0,0.4)";
    el.title = `Driver: ${d.phone} (${d.status})`;

    const marker = new google.maps.marker.AdvancedMarkerElement({
      map: mapInstance.current,
      position: { lat: d.lat, lng: d.lng },
      content: el,
    });
    markersRef.current.push(marker);
  };

  const fetchSnapshot = async () => {
    try {
      const { data } = await api.get("/admin/live-map/snapshot/");

      // Clear old markers
      markersRef.current.forEach((m) => (m.map = null));
      markersRef.current = [];

      if (!mapInstance.current) return;

      // 1. Render Drivers (Green)
      data.drivers.forEach((d: any) => createDriverMarker(d));

      // 2. Render Rides (Blue=Pickup, Red=Drop)
      data.rides.forEach((r: any) => {
        // Pickup
        const pEl = document.createElement("div");
        pEl.style.width = "10px";
        pEl.style.height = "10px";
        pEl.style.borderRadius = "50%";
        pEl.style.background = "#3498db"; // Blue
        pEl.title = `Ride #${r.id} Pickup`;

        const pMarker = new google.maps.marker.AdvancedMarkerElement({
          map: mapInstance.current,
          position: r.pickup,
          content: pEl,
        });
        markersRef.current.push(pMarker);

        // Drop
        const dEl = document.createElement("div");
        dEl.style.width = "10px";
        dEl.style.height = "10px";
        dEl.style.background = "#e74c3c"; // Red
        dEl.style.transform = "rotate(45deg)";
        dEl.title = `Ride #${r.id} Drop`;

        const dMarker = new google.maps.marker.AdvancedMarkerElement({
          map: mapInstance.current,
          position: r.drop,
          content: dEl,
        });
        markersRef.current.push(dMarker);
      });

    } catch (err) {
      console.error("LiveMap polling error:", err);
    }
  };

  useEffect(() => {
    if (
      !mapRef.current ||
      !(window as any).google?.maps ||
      !(window as any).google.maps.marker
    ) {
      return;
    }

    // Initialize Map
    if (!mapInstance.current) {
      mapInstance.current = new google.maps.Map(mapRef.current, {
        center: { lat: 12.9716, lng: 77.5946 },
        zoom: 12,
        mapId: "ADMIN_LIVE_MAP",
      });
    }

    // Initial Fetch
    fetchSnapshot();

    // WebSocket Connection
    const token = localStorage.getItem("access");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/admin/live-map/?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("WS Connected");

    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        // Check if marker exists
        const existingMarker = markersRef.current.find(m => m.title?.includes(d.phone));

        if (existingMarker) {
          existingMarker.position = { lat: d.lat, lng: d.lng };
          // Optional: update color/status if changed
        } else {
          // Create new marker logic
          createDriverMarker(d);
        }
      } catch (err) {
        console.error("WS Message Error", err);
      }
    };

    ws.onerror = (e) => console.error("WS Error", e);
    ws.onclose = () => console.log("WS Disconnected");

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div style={{ height: "100vh", width: "100%" }}>
      <div ref={mapRef} style={{ height: "100%", width: "100%" }} />
    </div>
  );
}
