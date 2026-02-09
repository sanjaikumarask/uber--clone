export function interpolate(
  from: { lat: number; lng: number },
  to: { lat: number; lng: number },
  progress: number
) {
  return {
    lat: from.lat + (to.lat - from.lat) * progress,
    lng: from.lng + (to.lng - from.lng) * progress,
  };
}
