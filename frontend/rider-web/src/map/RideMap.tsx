import {
  GoogleMap,
  Marker,
  Polyline,
} from "@react-google-maps/api";
import { useMemo } from "react";
import { GOOGLE_MAPS_CONFIG } from "./map.config";

interface Props {
  driverLocation?: { lat: number; lng: number };
  pickup?: { lat: number; lng: number };
  drop?: { lat: number; lng: number };
  routePath?: { lat: number; lng: number }[];
}

export default function RideMap({
  driverLocation,
  pickup,
  drop,
  routePath,
}: Props) {
  const center = useMemo(() => {
    return driverLocation || pickup || GOOGLE_MAPS_CONFIG.defaultCenter;
  }, [driverLocation, pickup]);

  return (
    <GoogleMap
      mapContainerStyle={{
        width: "100%",
        height: "400px",
      }}
      center={center}
      zoom={GOOGLE_MAPS_CONFIG.defaultZoom}
      options={{
        disableDefaultUI: true,
        zoomControl: true,
      }}
    >
      {pickup && <Marker position={pickup} label="P" />}
      {drop && <Marker position={drop} label="D" />}

      {driverLocation && (
        <Marker
          position={driverLocation}
          icon={{
            url: "/car-marker.png", // optional
            scaledSize: new google.maps.Size(40, 40),
          }}
        />
      )}

      {routePath && (
        <Polyline
          path={routePath}
          options={{
            strokeColor: "#000",
            strokeOpacity: 0.8,
            strokeWeight: 4,
          }}
        />
      )}
    </GoogleMap>
  );
}
