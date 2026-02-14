import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";
import { useEffect, useRef } from "react";
import { useRideStore } from "../domains/rides/ride.store";
import AnimatedDriverMarker from "./AnimatedDriverMarker";

const LIBRARIES: ("marker")[] = ["marker"];

interface Props {
  center: { lat: number; lng: number };
}

export default function MapView({ center }: Props) {
  // ✅ FIXED ENV VARIABLE NAME
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: apiKey,
    libraries: LIBRARIES,
  });

  const mapRef = useRef<google.maps.Map | null>(null);

  const driverLocation = useRideStore((s) => s.driverLocation);
  const status = useRideStore((s) => s.status);

  useEffect(() => {
    if (!mapRef.current) return;
    (window as any).__ACTIVE_MAP__ = mapRef.current;
  }, [isLoaded]);

  useEffect(() => {
    if (!mapRef.current || !driverLocation) return;

    if (["ASSIGNED", "ARRIVED", "ONGOING"].includes(status ?? "")) {
      mapRef.current.panTo(driverLocation);
    }
  }, [driverLocation, status]);

  if (!isLoaded) return <p>Loading map…</p>;

  return (
    <GoogleMap
      onLoad={(map) => {
        mapRef.current = map;
      }}
      center={center}
      zoom={15}
      mapContainerStyle={{ width: "100%", height: "400px" }}
      options={{
        disableDefaultUI: true,
        zoomControl: true,
        gestureHandling: "greedy",
      }}
    >
      <AnimatedDriverMarker
        from={center}
        to={center}
        isStatic
        icon="/car.png"
      />

      {driverLocation && (
        <AnimatedDriverMarker
          from={driverLocation}
          to={driverLocation}
          duration={800}
        />
      )}
    </GoogleMap>
  );
}
