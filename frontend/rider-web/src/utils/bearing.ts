export function getBearing(
  from: { lat: number; lng: number },
  to: { lat: number; lng: number }
) {
  const toRad = (d: number) => (d * Math.PI) / 180;

  const y =
    Math.sin(toRad(to.lng - from.lng)) * Math.cos(toRad(to.lat));
  const x =
    Math.cos(toRad(from.lat)) * Math.sin(toRad(to.lat)) -
    Math.sin(toRad(from.lat)) *
      Math.cos(toRad(to.lat)) *
      Math.cos(toRad(to.lng - from.lng));

  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}
