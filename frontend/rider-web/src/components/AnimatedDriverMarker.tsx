// src/components/AnimatedDriverMarker.tsx
// Fixed version — handles LatLng functions, smooth road-following interpolation.

import { useEffect, useRef } from "react";
import { interpolate } from "../utils/interpolate";
import { getBearing } from "../utils/bearing";

interface Props {
  map: google.maps.Map;
  from: { lat: number; lng: number };
  to: { lat: number; lng: number };
  heading?: number | null;
  duration?: number;
  vehicleType?: string | null;
  path?: google.maps.LatLng[]; // NEW: Path to follow if available
}

const VEHICLE_ICONS: Record<string, string> = {
  moto: "/assets/vehicles/moto.png",
  auto: "/assets/vehicles/auto.png",
  go: "/assets/vehicles/go.png",
  xl: "/assets/vehicles/xl.png",
};

/** Safely extract a number from a Google Maps LatLng value (function or plain number). */
function extractCoord(position: any, key: "lat" | "lng"): number {
  if (!position) return 0;
  const val = position[key];
  if (typeof val === "function") return val();
  return typeof val === "number" ? val : 0;
}

export default function AnimatedDriverMarker({
  map,
  from,
  to,
  heading,
  duration = 2000,
  vehicleType = "go",
  path,
}: Props) {
  const markerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(null);
  const animRef = useRef<number | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  // ── 1. Create marker once when map is ready ──────────────────────────────
  useEffect(() => {
    if (!window.google?.maps?.marker?.AdvancedMarkerElement) {
      console.error("[Marker] AdvancedMarkerElement unavailable.");
      return;
    }
    if (markerRef.current) return;

    const icon = VEHICLE_ICONS[vehicleType || "go"] ?? VEHICLE_ICONS.go;

    const img = document.createElement("img");
    img.src = icon;
    img.style.width = "40px";
    img.style.height = "40px";
    img.style.objectFit = "contain";
    img.style.transformOrigin = "center center";
    img.style.filter = "drop-shadow(0 2px 4px rgba(0,0,0,0.4))";
    img.style.transition = "transform 0.4s ease-out";
    imgRef.current = img;

    try {
      markerRef.current = new google.maps.marker.AdvancedMarkerElement({
        position: { lat: from.lat, lng: from.lng },
        content: img,
        map,
        zIndex: 100,
      });
    } catch (err) {
      console.error("[Marker] ❌ Creation failed:", err);
    }

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      if (markerRef.current) {
        markerRef.current.map = null;
        markerRef.current = null;
      }
    };
  }, [map]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── 2. Update icon
  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    const icon = VEHICLE_ICONS[vehicleType || "go"] ?? VEHICLE_ICONS.go;
    if (img.src !== icon) {
      img.src = icon;
    }
  }, [vehicleType]);

  // ── 3. Animate marker
  useEffect(() => {
    const marker = markerRef.current;
    if (!marker || !window.google?.maps) return;
    if (isNaN(to.lat) || isNaN(to.lng)) return;

    const startPos = {
      lat: extractCoord(marker.position, "lat"),
      lng: extractCoord(marker.position, "lng"),
    };
    const animFrom = (startPos.lat === 0 && startPos.lng === 0) ? from : startPos;

    // --- Road Following Logic ---
    let subPath: { lat: number, lng: number }[] = [];
    if (path && path.length > 1) {
      try {
        const spherical = google.maps.geometry.spherical;
        const fromLatLng = new google.maps.LatLng(animFrom.lat, animFrom.lng);
        const toLatLng = new google.maps.LatLng(to.lat, to.lng);

        // Find segments on the path closest to current and target positions
        let minFromDist = Infinity;
        let fromIdx = -1;
        let minToDist = Infinity;
        let toIdx = -1;

        for (let i = 0; i < path.length; i++) {
          const dFrom = spherical.computeDistanceBetween(fromLatLng, path[i]);
          if (dFrom < minFromDist) {
            minFromDist = dFrom;
            fromIdx = i;
          }
          const dTo = spherical.computeDistanceBetween(toLatLng, path[i]);
          if (dTo < minToDist) {
            minToDist = dTo;
            toIdx = i;
          }
        }

        // If we found a valid forward path segment (within 100m tolerance)
        if (fromIdx !== -1 && toIdx !== -1 && fromIdx < toIdx && minFromDist < 100 && minToDist < 100) {
          subPath = [
            animFrom,
            ...path.slice(fromIdx + 1, toIdx).map(p => ({ lat: p.lat(), lng: p.lng() })),
            to
          ];
        }
      } catch (e) {
        console.warn("[Animation] Path interpolation error:", e);
      }
    }

    const start = performance.now();

    const tick = (now: number) => {
      if (!markerRef.current) return;
      const progress = Math.min((now - start) / duration, 1);

      let currentPos;
      if (subPath.length > 2) {
        // Interpolate along multiple segments
        const totalSegments = subPath.length - 1;
        const segmentIdx = Math.min(Math.floor(progress * totalSegments), totalSegments - 1);
        const segmentProgress = (progress * totalSegments) - segmentIdx;

        currentPos = interpolate(subPath[segmentIdx], subPath[segmentIdx + 1], segmentProgress);

        // Dynamic Heading along the route
        const img = imgRef.current;
        if (img?.style && segmentIdx < totalSegments) {
          const b = getBearing(subPath[segmentIdx].lat, subPath[segmentIdx].lng, subPath[segmentIdx + 1].lat, subPath[segmentIdx + 1].lng);
          img.style.transform = `rotate(${b}deg)`;
        }
      } else {
        // Simple linear fallback
        currentPos = interpolate(animFrom, to, progress);
        const img = imgRef.current;
        const bearing = (heading != null) ? heading : getBearing(animFrom.lat, animFrom.lng, to.lat, to.lng);
        if (img?.style) img.style.transform = `rotate(${bearing}deg)`;
      }

      markerRef.current.position = currentPos;

      if (progress < 1) {
        animRef.current = requestAnimationFrame(tick);
      }
    };

    if (animRef.current) cancelAnimationFrame(animRef.current);
    animRef.current = requestAnimationFrame(tick);
  }, [to.lat, to.lng, heading, duration, path]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}