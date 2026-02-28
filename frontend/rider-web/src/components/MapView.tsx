import { GoogleMap, useJsApiLoader, Polyline } from "@react-google-maps/api";
import { useEffect, useState, useMemo, useRef } from "react";
import { useRideStore } from "../domains/rides/ride.store";
import AnimatedDriverMarker from "./AnimatedDriverMarker";

const LIBRARIES: ("marker" | "geometry" | "places")[] = ["marker", "geometry", "places"];

interface Props {
  center: { lat: number; lng: number };
  onMapClick?: (e: google.maps.MapMouseEvent) => void;
  nearbyDrivers?: any[];
}

// 🗺️ Uber-like Map Style (Minimalist Grayscale)
const UBER_MAP_STYLE = [
  { "elementType": "geometry", "stylers": [{ "color": "#f5f5f5" }] },
  { "elementType": "labels.icon", "stylers": [{ "visibility": "off" }] },
  { "elementType": "labels.text.fill", "stylers": [{ "color": "#616161" }] },
  { "elementType": "labels.text.stroke", "stylers": [{ "color": "#f5f5f5" }] },
  { "featureType": "administrative.land_parcel", "elementType": "labels.text.fill", "stylers": [{ "color": "#bdbdbd" }] },
  { "featureType": "poi", "elementType": "geometry", "stylers": [{ "color": "#eeeeee" }] },
  { "featureType": "poi", "elementType": "labels.text.fill", "stylers": [{ "color": "#757575" }] },
  { "featureType": "road", "elementType": "geometry", "stylers": [{ "color": "#ffffff" }] },
  { "featureType": "road.arterial", "elementType": "labels.text.fill", "stylers": [{ "color": "#757575" }] },
  { "featureType": "road.highway", "elementType": "geometry", "stylers": [{ "color": "#dadada" }] },
  { "featureType": "road.highway", "elementType": "labels.text.fill", "stylers": [{ "color": "#616161" }] },
  { "featureType": "road.local", "elementType": "labels.text.fill", "stylers": [{ "color": "#9e9e9e" }] },
  { "featureType": "transit.line", "elementType": "geometry", "stylers": [{ "color": "#e5e5e5" }] },
  { "featureType": "transit.station", "elementType": "geometry", "stylers": [{ "color": "#eeeeee" }] },
  { "featureType": "water", "elementType": "geometry", "stylers": [{ "color": "#c9c9c9" }] },
  { "featureType": "water", "elementType": "labels.text.fill", "stylers": [{ "color": "#9e9e9e" }] }
];

export default function MapView({ center, onMapClick, nearbyDrivers = [] }: Props) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: apiKey,
    libraries: LIBRARIES,
    version: "beta",
  });

  const [mapInstance, setMapInstance] = useState<google.maps.Map | null>(null);

  const driverLocation = useRideStore((s) => s.driverLocation);
  const prevLocation = useRideStore((s) => s.driverPrevLocation);
  const heading = useRideStore((s) => s.heading);
  const status = useRideStore((s) => s.status);
  const encodedPolyline = useRideStore((s) => s.polyline);
  const pickup = useRideStore((s) => s.pickup);
  const dropoff = useRideStore((s) => s.dropoff);
  const completedRoute = useRideStore((s) => s.completedRoute);

  const vehicleType = useRideStore((s) => s.vehicleType);

  // Decode polyline only when isLoaded and encodedPolyline exist
  const path = useMemo(() => {
    if (!isLoaded || !encodedPolyline || !window.google) return [];
    try {
      return google.maps.geometry.encoding.decodePath(encodedPolyline);
    } catch (e) {
      console.error("Failed to decode polyline:", e);
      return [];
    }
  }, [isLoaded, encodedPolyline]);

  useEffect(() => {
    if (!mapInstance || !isLoaded || !window.google) return;

    const bounds = new google.maps.LatLngBounds();
    let hasCoords = false;
    const isValid = (loc: any) => loc && typeof loc.lat === 'number' && typeof loc.lng === 'number';

    if (isValid(driverLocation)) {
      bounds.extend(driverLocation!);
      hasCoords = true;
    }

    const activePoint = (status === "ASSIGNED" || status === "ARRIVED") ? pickup : (status === "ONGOING" ? dropoff : null);

    if (isValid(activePoint)) {
      bounds.extend(activePoint!);
      hasCoords = true;
    }

    if (hasCoords) {
      const coordsCount = (isValid(driverLocation) ? 1 : 0) + (isValid(activePoint) ? 1 : 0);

      if (coordsCount > 1) {
        mapInstance.fitBounds(bounds, {
          top: 80, right: 80, bottom: 80, left: 80
        });
      } else if (isValid(driverLocation) && mapInstance) {
        mapInstance.panTo(driverLocation!);
        if (mapInstance.getZoom() !== undefined && mapInstance.getZoom()! < 15) {
          mapInstance.setZoom(15);
        }
      }
    }
  }, [driverLocation, pickup, dropoff, status, mapInstance, isLoaded]);

  if (!isLoaded) return <p style={{ padding: 20 }}>Loading map…</p>;

  return (
    <GoogleMap
      onLoad={(map) => {
        setMapInstance(map);
        // Apply grayscale style after a brief delay to bypass mapId restriction
        setTimeout(() => {
          try { (map as any).setOptions({ styles: UBER_MAP_STYLE }); } catch (_) { }
        }, 300);
      }}
      onClick={onMapClick}
      center={center}
      zoom={14}
      mapContainerStyle={{ width: "100%", height: "100%" }}
      options={{
        disableDefaultUI: true,
        zoomControl: false,
        gestureHandling: "greedy",
        mapId: "ac584fdc61f9c23a0aecc050",
      }}
    >
      {path.length > 0 && (
        <>
          {/* Main Background (Planned Route) - Grey with black outline */}
          <Polyline
            path={path}
            options={{
              strokeColor: "#000",
              strokeOpacity: 0.15,
              strokeWeight: 9,
              zIndex: 1,
            }}
          />
          <Polyline
            path={path}
            options={{
              strokeColor: "#333", // Dark grey
              strokeOpacity: 0.8,
              strokeWeight: 5,
              zIndex: 2,
            }}
          />

          {/* Progress Path (Driven Route) - Blue with glow */}
          <Polyline
            path={completedRoute}
            options={{
              strokeColor: "#fff",
              strokeOpacity: 0.3,
              strokeWeight: 8,
              zIndex: 3,
            }}
          />
          <Polyline
            path={completedRoute}
            options={{
              strokeColor: "#276EF1", // Uber Blue
              strokeOpacity: 1.0,
              strokeWeight: 5,
              zIndex: 4,
            }}
          />
        </>
      )}
      {mapInstance && driverLocation && (
        <AnimatedDriverMarker
          map={mapInstance}
          from={prevLocation || driverLocation}
          to={driverLocation}
          heading={heading}
          duration={2000}
          vehicleType={vehicleType}
          path={path}
        />
      )}

      {/* Pickup Marker (Green Dot / Black Circle) */}
      {mapInstance && pickup && (
        <CustomMarker
          map={mapInstance}
          position={pickup}
          label="P"
          title="Pickup Location"
        />
      )}

      {/* Dropoff Marker */}
      {mapInstance && dropoff && (
        <CustomMarker
          map={mapInstance}
          position={dropoff}
          color="#ef4444"
          label="D"
          title="Destination"
        />
      )}

      {/* Nearby Drivers Markers */}
      {mapInstance && nearbyDrivers && nearbyDrivers.length > 0 && nearbyDrivers.map(d => (
        <CustomMarker
          key={`nearby-${d.id}`}
          map={mapInstance}
          position={{ lat: d.lat, lng: d.lng }}
          label="CAR"
          vehicleType={d.vehicle_type}
          title={d.name}
        />
      ))}

      {/* Rider's Current Position (Blue Dot) */}
      <RiderLocationDot map={mapInstance} isLoaded={isLoaded} />
    </GoogleMap>
  );
}

import { sendRiderLocation } from "../domains/tracking/tracking.socket";

function RiderLocationDot({ map, isLoaded }: { map: any, isLoaded: boolean }) {
  const [pos, setPos] = useState<google.maps.LatLngLiteral | null>(null);

  const lastUpdateRef = useRef<number>(0);

  useEffect(() => {
    if (!isLoaded || !map) return;
    const watchId = navigator.geolocation.watchPosition(
      (p) => {
        const newPos = { lat: p.coords.latitude, lng: p.coords.longitude };
        setPos(newPos);

        // Throttle updates to backend (10 seconds)
        const now = Date.now();
        if (now - lastUpdateRef.current > 10000) {
          sendRiderLocation(newPos.lat, newPos.lng);
          lastUpdateRef.current = now;
        }
      },
      (err) => console.warn("Geo error", err),
      { enableHighAccuracy: true }
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, [isLoaded, map]);

  useEffect(() => {
    if (!map || !pos || isNaN(pos.lat) || isNaN(pos.lng)) return;
    const dot = document.createElement("div");
    dot.style.cssText = `
      width: 16px; height: 16px; background: #2970ff; 
      border-radius: 50%; border: 3px solid #fff;
      box-shadow: 0 0 10px rgba(41,112,255,0.6);
    `;
    const marker = new google.maps.marker.AdvancedMarkerElement({
      position: pos,
      map,
      title: "Your Location",
      content: dot
    });
    return () => { marker.map = null; };
  }, [map, pos]);

  return null;
}

/** 
 * Simple wrapper for AdvancedMarkerElement since @react-google-maps/api 
 * doesn't have a high-level component for it yet.
 */
function CustomMarker({ map, position, label, title, vehicleType }: any) {
  const lat = Number(position?.lat);
  const lng = Number(position?.lng);
  const isValid = !isNaN(lat) && !isNaN(lng);

  useEffect(() => {
    if (!map || !isValid) {
      if (!isValid) console.warn(`[CustomMarker] Invalid position for ${label || title}:`, position);
      return;
    }

    const marker = new google.maps.marker.AdvancedMarkerElement({
      position: { lat, lng },
      map,
      title,
      content: createUberMarkerElement(label, vehicleType),
    });

    return () => { marker.map = null; };
  }, [map, lat, lng, label, title, isValid, vehicleType]);

  return null;
}

const VEHICLE_ICONS: Record<string, string> = {
  moto: "/assets/vehicles/moto.png",
  auto: "/assets/vehicles/auto.png",
  go: "/assets/vehicles/go.png",
  xl: "/assets/vehicles/xl.png",
};

function createUberMarkerElement(label: string, vehicleType?: string) {
  const div = document.createElement("div");
  const isPickup = label === "P";
  const isDropoff = label === "D";
  const isCar = label?.toUpperCase() === "CAR" || label?.toUpperCase() === "VEHICLE";

  if (isCar || (!isPickup && !isDropoff)) {
    const img = document.createElement("img");
    img.src = VEHICLE_ICONS[vehicleType || "go"] || VEHICLE_ICONS.go;
    img.style.cssText = `
      width: 40px; height: 40px; 
      object-fit: contain;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));
    `;
    return img;
  }

  div.style.cssText = `
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; 
    background: ${isPickup ? "#000" : "#ef4444"};
    border-radius: ${isPickup ? "50%" : "2px"}; 
    border: 3px solid #fff; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    color: #fff; font-family: sans-serif; font-weight: 900; font-size: 12px;
    transform: perspective(40px) ${isPickup ? "" : "rotateX(20deg)"};
  `;
  div.textContent = label;
  return div;
}
