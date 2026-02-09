import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";
import { useEffect, useRef } from "react";
import { useRideStore } from "../store/ride.store";
import AnimatedDriverMarker from "./AnimatedDriverMarker";

const LIBRARIES: ("marker")[] = ["marker"]; // ✅ STATIC

interface Props {
  center: { lat: number; lng: number };
}

export default function MapView({ center }: Props) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_KEY as string;

  if (!apiKey) {
    console.error("❌ Google Maps API key missing");
  }

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: apiKey,
    libraries: LIBRARIES, // ✅ STABLE reference
  });

  const mapRef = useRef<google.maps.Map | null>(null);

  const driverLocation = useRideStore((s) => s.driverLocation);
  const prevDriverLocation = useRideStore((s) => s.prevDriverLocation);
  const status = useRideStore((s) => s.status);

  useEffect(() => {
    if (!mapRef.current || !driverLocation) return;

    if (["ASSIGNED", "ARRIVED", "ONGOING"].includes(status)) {
      mapRef.current.panTo(driverLocation);
    }
  }, [driverLocation, status]);

  if (!isLoaded) return <p>Loading map…</p>;

  return (
    <GoogleMap
      onLoad={(map) => (mapRef.current = map)}
      center={center}
      zoom={15}
      mapContainerStyle={{ width: "100%", height: "400px" }}
      options={{
        disableDefaultUI: true,
        zoomControl: true,
        gestureHandling: "greedy",
      }}
    >
      {/* Rider (static marker) */}
      <AnimatedDriverMarker
        from={center}
        to={center}
        isStatic
        icon="/car.png"
      />

      {/* Driver (animated marker) */}
      {driverLocation && prevDriverLocation && (
        <AnimatedDriverMarker
          from={prevDriverLocation}
          to={driverLocation}
          duration={800}
        />
      )}
    </GoogleMap>
  );
}
