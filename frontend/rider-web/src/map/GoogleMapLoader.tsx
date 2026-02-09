import { LoadScript } from "@react-google-maps/api";
import { GOOGLE_MAPS_CONFIG } from "./map.config";

export default function GoogleMapLoader({
  children,
}: {
  children: JSX.Element;
}) {
  return (
    <LoadScript
      googleMapsApiKey={GOOGLE_MAPS_CONFIG.apiKey}
      libraries={GOOGLE_MAPS_CONFIG.libraries}
      loadingElement={<div>Loading map...</div>}
    >
      {children}
    </LoadScript>
  );
}
