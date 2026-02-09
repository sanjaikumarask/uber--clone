export const GOOGLE_MAPS_CONFIG = {
  apiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
  libraries: ["places"] as (
    | "places"
    | "geometry"
    | "drawing"
    | "visualization"
  )[],
  defaultCenter: {
    lat: 12.9716, // Bangalore example
    lng: 77.5946,
  },
  defaultZoom: 14,
};
