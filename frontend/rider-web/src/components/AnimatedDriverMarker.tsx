import { useEffect, useRef } from "react";
import { interpolate } from "../utils/interpolate";
import { getBearing } from "../utils/bearing";

interface Props {
  from: { lat: number; lng: number };
  to: { lat: number; lng: number };
  duration?: number;
  isStatic?: boolean;
  icon?: string;
}

export default function AnimatedDriverMarker({
  from,
  to,
  duration = 800,
  isStatic = false,
  icon = "/car.png",
}: Props) {
  const markerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(
    null
  );

  useEffect(() => {
    if (!window.google?.maps) return;

    if (!markerRef.current) {
      const img = document.createElement("img");
      img.src = icon;
      img.style.width = "32px";
      img.style.transformOrigin = "center";

      markerRef.current = new google.maps.marker.AdvancedMarkerElement({
        position: from,
        content: img,
        map: (window as any).__ACTIVE_MAP__, // injected globally
      });
    }

    if (!window.google?.maps || !markerRef.current) return;

    if (isStatic) {
      markerRef.current.position = from;
      return;
    }

    const start = performance.now();
    const bearing = getBearing(from.lat, from.lng, to.lat, to.lng);
    const img = markerRef.current.content as HTMLImageElement;

    // Guard against element being removed or unmounted
    if (!img) return;

    const animate = (now: number) => {
      // Check ref again inside RAF loop
      if (!markerRef.current) return;

      const progress = Math.min((now - start) / duration, 1);
      const pos = interpolate(from, to, progress);

      markerRef.current.position = pos;
      if (img && img.style) {
        img.style.transform = `rotate(${bearing}deg)`;
      }

      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [from, to, duration, isStatic, icon]);

  return null;
}
