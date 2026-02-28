import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useJsApiLoader, Autocomplete } from "@react-google-maps/api";
import { useRideStore } from "../domains/rides/ride.store";
import MapView from "../components/MapView";
import { api } from "../services/http";

const LIBRARIES: ("marker" | "geometry" | "places")[] = ["marker", "geometry", "places"];
const CHENNAI_CENTER = { lat: 13.0827, lng: 80.2707 };

// ── Vehicle Types ────────────────────────────────────────────────────────────
const VEHICLE_TYPES = [
  {
    id: "moto",
    name: "Uber Moto",
    icon: "/assets/vehicles/moto.png",
    multiplier: 0.55,
    desc: "Fastest · 1 seat",
    tag: "CHEAPEST",
    tagColor: "#22c55e",
    accent: "#22c55e",
    seats: 1,
  },
  {
    id: "auto",
    name: "Uber Auto",
    icon: "/assets/vehicles/auto.png",
    multiplier: 0.75,
    desc: "No AC · Comfy for 3",
    tag: "POPULAR",
    tagColor: "#f59e0b",
    accent: "#f59e0b",
    seats: 3,
  },
  {
    id: "go",
    name: "UberGo",
    icon: "/assets/vehicles/go.png",
    multiplier: 1.0,
    desc: "Affordable, compact rides",
    tag: null,
    tagColor: "transparent",
    accent: "#276EF1",
    seats: 4,
  },
  {
    id: "xl",
    name: "UberXL",
    icon: "/assets/vehicles/xl.png",
    multiplier: 1.4,
    desc: "Comfortable SUVs for groups",
    tag: null,
    tagColor: "transparent",
    accent: "#8b5cf6",
    seats: 6,
  },
];

export default function BookRide() {
  const navigate = useNavigate();
  const apiKey = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string) || "";

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: apiKey,
    libraries: LIBRARIES,
    version: "beta",
  });

  const {
    pickup, pickupAddress, dropoff, dropoffAddress,
    setPickup, setDropoff, setPolyline, setFare,
    createRide, checkActiveRide
  } = useRideStore();

  const [pickupInput, setPickupInput] = useState(pickupAddress || "");
  const [dropoffInput, setDropoffInput] = useState(dropoffAddress || "");
  const [focusedField, setFocusedField] = useState<"pickup" | "dropoff">("dropoff");
  const [estimating, setEstimating] = useState(false);
  const [baseFare, setBaseFare] = useState<number | null>(null);
  const [routeInfo, setRouteInfo] = useState<{ distance: string; duration: string } | null>(null);
  const [selectedVehicle, setSelectedVehicle] = useState(VEHICLE_TYPES[2]); // default UberGo
  const [confirming, setConfirming] = useState(false);

  const pickupAutocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const dropoffAutocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);

  const handleMapClick = (e: google.maps.MapMouseEvent) => {
    if (!e.latLng) return;
    const loc = { lat: e.latLng.lat(), lng: e.latLng.lng() };
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ location: loc }, (results, status) => {
      if (status === "OK" && results?.[0]) {
        const address = results[0].formatted_address;
        if (focusedField === "pickup") { setPickup(loc, address); setPickupInput(address); }
        else { setDropoff(loc, address); setDropoffInput(address); }
      }
    });
  };

  const [nearbyDrivers, setNearbyDrivers] = useState<any[]>([]);

  useEffect(() => {
    if (!pickup?.lat || !pickup?.lng) return;

    const fetchNearby = async () => {
      try {
        const res = await api.post("/rides/nearby-drivers/", {
          lat: pickup.lat,
          lng: pickup.lng,
          radius_km: 20
        });
        console.log(`[BookRide] Found ${res.data.drivers?.length || 0} drivers nearby (Total Online: ${res.data.all_online_count})`, res.data.drivers);
        setNearbyDrivers(res.data.drivers || []);
      } catch (err: any) {
        console.error("Failed to fetch nearby drivers", err?.response?.data || err.message);
      }
    };

    fetchNearby();
    const interval = setInterval(fetchNearby, 2000);
    return () => clearInterval(interval);
  }, [pickup]);

  useEffect(() => {
    if (pickup && dropoff) handleEstimateFare();
    else setBaseFare(null);
  }, [pickup, dropoff]);

  const handleEstimateFare = async () => {
    if (!pickup?.lat || !pickup?.lng || !dropoff?.lat || !dropoff?.lng) return;
    setEstimating(true);
    try {
      const res = await api.post("/rides/estimate-fare/", {
        pickup_lat: pickup.lat,
        pickup_lng: pickup.lng,
        drop_lat: dropoff.lat,
        drop_lng: dropoff.lng,
      });
      setBaseFare(res.data.estimated_fare);
      setPolyline(res.data.polyline);
      setFare(res.data.estimated_fare);
      setRouteInfo({
        distance: `${Number(res.data.distance_km || 0).toFixed(1)} km`,
        duration: `${Math.ceil(res.data.duration_min)} mins`
      });
    } catch (err) {
      console.error("Fare estimate failed", err);
    } finally {
      setEstimating(false);
    }
  };

  const onPickupLoad = (ac: google.maps.places.Autocomplete) => { pickupAutocompleteRef.current = ac; };
  const onDropoffLoad = (ac: google.maps.places.Autocomplete) => { dropoffAutocompleteRef.current = ac; };

  const onPickupPlaceChanged = () => {
    const place = pickupAutocompleteRef.current?.getPlace();
    if (place?.geometry?.location) {
      const loc = { lat: place.geometry.location.lat(), lng: place.geometry.location.lng() };
      setPickup(loc, place.formatted_address || place.name);
      setPickupInput(place.formatted_address || place.name || "");
    }
  };

  const onDropoffPlaceChanged = () => {
    const place = dropoffAutocompleteRef.current?.getPlace();
    if (place?.geometry?.location) {
      const loc = { lat: place.geometry.location.lat(), lng: place.geometry.location.lng() };
      setDropoff(loc, place.formatted_address || place.name);
      setDropoffInput(place.formatted_address || place.name || "");
    }
  };

  const handleConfirmRequest = async () => {
    if (!pickup || !dropoff || confirming) return;
    setConfirming(true);
    try {
      const active = await checkActiveRide();
      if (active?.ride_id) { navigate("/ride/searching"); return; }

      await createRide({
        pickup_lat: pickup.lat,
        pickup_lng: pickup.lng,
        pickup_address: pickupAddress || pickupInput,
        drop_lat: dropoff.lat,
        drop_lng: dropoff.lng,
        drop_address: dropoffAddress || dropoffInput,
        vehicle_type: selectedVehicle.id,
      });

      navigate("/ride/searching");
    } catch {
      alert("Failed to request ride. Please try again.");
    } finally {
      setConfirming(false);
    }
  };

  if (!isLoaded) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "#000", color: "#fff" }}>
        Loading Maps...
      </div>
    );
  }

  const fare = (vt: typeof VEHICLE_TYPES[0]) =>
    baseFare != null ? `₹${Math.round(baseFare * vt.multiplier)}` : "—";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", position: "relative", background: "#000" }}>

      {/* ── Search Header ── */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, zIndex: 100,
        background: "rgba(10,10,10,0.92)", backdropFilter: "blur(16px)",
        borderRadius: "0 0 20px 20px", borderBottom: "1px solid rgba(255,255,255,0.08)",
        padding: "16px 20px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <button
            onClick={() => navigate(-1)}
            style={{ width: 36, height: 36, borderRadius: "50%", border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.06)", color: "#fff", cursor: "pointer", fontSize: 16, flexShrink: 0 }}
          >
            ←
          </button>
          <h1 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 700, color: "#fff" }}>Plan your ride</h1>
        </div>

        {/* Pickup */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#fff", flexShrink: 0 }} />
          <Autocomplete onLoad={onPickupLoad} onPlaceChanged={onPickupPlaceChanged}>
            <input
              style={inputStyle(focusedField === "pickup", "#fff")}
              placeholder="Starting point?"
              value={pickupInput}
              onChange={(e) => setPickupInput(e.target.value)}
              onFocus={() => setFocusedField("pickup")}
            />
          </Autocomplete>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 10, background: "rgba(255,255,255,0.15)", marginLeft: 3, marginBottom: 8 }} />

        {/* Dropoff */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 8, height: 8, borderRadius: 2, background: "#276EF1", flexShrink: 0 }} />
          <Autocomplete onLoad={onDropoffLoad} onPlaceChanged={onDropoffPlaceChanged}>
            <input
              style={inputStyle(focusedField === "dropoff", "#276EF1")}
              placeholder="Where to?"
              value={dropoffInput}
              onChange={(e) => setDropoffInput(e.target.value)}
              onFocus={() => setFocusedField("dropoff")}
            />
          </Autocomplete>
        </div>
      </div>

      {/* ── Map ── */}
      <div style={{ flex: 1, height: "100vh" }}>
        <MapView
          center={CHENNAI_CENTER}
          onMapClick={handleMapClick}
          nearbyDrivers={nearbyDrivers}
        />
      </div>

      {/* ── Fare / Vehicle Drawer ── */}
      {baseFare !== null && (
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 100,
          background: "rgba(10,10,10,0.97)", backdropFilter: "blur(20px)",
          borderRadius: "24px 24px 0 0",
          borderTop: "1px solid rgba(255,255,255,0.1)",
          padding: "20px 20px 28px",
        }}>

          {/* Route info */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <span style={{ color: "#A6A6A6", fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Choose a ride
            </span>
            {routeInfo && (
              <span style={{ color: "#A6A6A6", fontSize: 12 }}>
                {routeInfo.distance} · {routeInfo.duration}
              </span>
            )}
          </div>

          {/* Vehicle list */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
            {VEHICLE_TYPES.map((vt) => {
              const selected = selectedVehicle.id === vt.id;
              return (
                <div
                  key={vt.id}
                  onClick={() => setSelectedVehicle(vt)}
                  style={{
                    display: "flex", alignItems: "center", gap: 14,
                    padding: "14px 16px",
                    borderRadius: 14,
                    border: selected ? `2px solid ${vt.accent}` : "1px solid rgba(255,255,255,0.10)",
                    background: selected ? `rgba(${hexToRgb(vt.accent)}, 0.08)` : "rgba(255,255,255,0.04)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  {/* Left — image */}
                  <img src={vt.icon} alt={vt.name} style={{ width: 60, height: 40, objectFit: "contain", flexShrink: 0 }} />

                  {/* Middle — name + desc */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#fff" }}>{vt.name}</span>
                      {vt.tag && (
                        <span style={{
                          background: `rgba(${hexToRgb(vt.tagColor!)}, 0.15)`,
                          color: vt.tagColor,
                          fontSize: 10, fontWeight: 700,
                          padding: "2px 6px", borderRadius: 4,
                          textTransform: "uppercase", letterSpacing: "0.05em",
                        }}>
                          {vt.tag}
                        </span>
                      )}
                    </div>
                    <span style={{ color: "#A6A6A6", fontSize: 12 }}>{vt.desc}</span>
                  </div>

                  {/* Right — price */}
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ fontWeight: 800, fontSize: "1.1rem", color: selected ? vt.accent : "#fff" }}>
                      {estimating ? "…" : fare(vt)}
                    </div>
                    <div style={{ color: "#666", fontSize: 11 }}>
                      👥 {vt.seats} {vt.seats === 1 ? "seat" : "seats"}
                    </div>
                  </div>

                  {/* Selection indicator */}
                  {selected && (
                    <div style={{
                      position: "absolute", top: 10, right: 10,
                      width: 18, height: 18, borderRadius: "50%",
                      background: vt.accent, display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <span style={{ color: "#fff", fontSize: 11, fontWeight: 900 }}>✓</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Confirm button */}
          <button
            onClick={handleConfirmRequest}
            disabled={confirming || estimating}
            style={{
              width: "100%",
              padding: "17px 0",
              background: selectedVehicle.accent,
              color: "#fff",
              fontWeight: 700,
              fontSize: "1rem",
              border: "none",
              borderRadius: 12,
              cursor: confirming ? "not-allowed" : "pointer",
              opacity: confirming ? 0.75 : 1,
              transition: "opacity 0.15s",
              letterSpacing: "0.01em",
            }}
          >
            {confirming ? "Booking…" : `Confirm ${selectedVehicle.name}`}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function inputStyle(focused: boolean, accent: string): React.CSSProperties {
  return {
    width: "100%",
    background: focused ? "rgba(255,255,255,0.07)" : "transparent",
    border: "none",
    borderBottom: `1.5px solid ${focused ? accent : "rgba(255,255,255,0.12)"}`,
    color: "#fff",
    fontSize: "0.95rem",
    padding: "8px 4px",
    outline: "none",
    transition: "border-color 0.2s",
    fontFamily: "inherit",
  };
}

function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return "255,255,255";
  return `${parseInt(result[1], 16)},${parseInt(result[2], 16)},${parseInt(result[3], 16)}`;
}
