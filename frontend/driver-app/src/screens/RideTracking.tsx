import React, { useState, useEffect, useRef } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, TextInput, Image } from "react-native";
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from "react-native-maps";
import { api } from "../services/api";
import * as Location from "expo-location";
import {
  connectLocationSocket,
  sendLocation,
  onRidesEvent,
  connectRideSocket,
  disconnectRideSocket,
  onRideEvent,
  sendRideChat,
} from "../services/socket";
import { decodePolyline, LatLng } from "../services/utils";

const GOOGLE_MAPS_API_KEY = "AIzaSyD5Yq_dZsNz5fbq2DAAzjNfVKDYCn16BC8";

export default function RideTrackingScreen({ route, navigation }: any) {
  const { rideId } = route.params || {};
  const [rideData, setRideData] = useState<any>(null);
  const [rideStatus, setRideStatus] = useState("ASSIGNED");
  const [otp, setOtp] = useState("");
  const locationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [currentLocation, setCurrentLocation] = useState<any>(null);
  const [path, setPath] = useState<LatLng[]>([]);
  const [routeInfo, setRouteInfo] = useState({ distance: "", duration: "" });
  const mapRef = useRef<MapView | null>(null);
  const lastRouteUpdateRef = useRef<number>(0);

  const [messages, setMessages] = useState<any[]>([]);
  const [chatOpen, setChatOpen] = useState(false);
  const [msgInput, setMsgInput] = useState("");

  const [showRating, setShowRating] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");

  // ── On mount: fetch ride state + start broadcasting location ──────
  useEffect(() => {
    fetchRideDetails();
    startLocationBroadcast();

    // Connect to specific ride socket for chat
    connectRideSocket(rideId);

    // Listen for status updates
    const unsubRides = onRidesEvent("ride_status_update", (msg) => {
      if (msg.ride_id && Number(msg.ride_id) !== Number(rideId)) return;
      if (msg.status) {
        setRideStatus(msg.status);
        if (msg.status === "COMPLETED") {
          setShowRating(true);
        } else if (msg.status === "CANCELLED") {
          Alert.alert("Ride Status", `Ride #${rideId} is CANCELLED`);
          navigation.replace("Home");
        }
      }
    });

    // Listen for chat messages
    const unsubChat = onRideEvent("NEW_CHAT_MESSAGE", (msg) => {
      setMessages(prev => [...prev, msg.payload]);
    });

    return () => {
      unsubRides();
      unsubChat();
      disconnectRideSocket();
      if (locationIntervalRef.current) clearInterval(locationIntervalRef.current);
      if (keepAliveRef.current) clearInterval(keepAliveRef.current);
    };
  }, []);

  async function triggerSOS() {
    Alert.alert(
      "Emergency SOS",
      "Are you in danger? This will alert the support team.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "YES, HELP!",
          onPress: async () => {
            try {
              await api.post(`supports/rides/${rideId}/sos/`, {
                lat: currentLocation?.latitude || 0,
                lng: currentLocation?.longitude || 0
              });
              Alert.alert("Success", "Emergency team notified.");
            } catch {
              Alert.alert("Error", "Failed to send SOS.");
            }
          }
        }
      ]
    );
  }

  // ── Trigger route update when status or location changes ───────────
  useEffect(() => {
    if (!currentLocation || !rideData) return;
    const now = Date.now();
    if (now - lastRouteUpdateRef.current < 15000) return;
    lastRouteUpdateRef.current = now;
    updateDynamicRoute();
  }, [rideStatus, currentLocation?.latitude, currentLocation?.longitude]);

  async function updateDynamicRoute() {
    if (!currentLocation || !rideData) return;
    let destination: { lat: number, lng: number } | null = null;
    if (rideStatus === "ASSIGNED") {
      destination = { lat: rideData.pickup_lat, lng: rideData.pickup_lng };
    } else if (rideStatus === "ONGOING") {
      destination = { lat: rideData.drop_lat, lng: rideData.drop_lng };
    }
    if (!destination) return;
    try {
      const origin = `${currentLocation.latitude},${currentLocation.longitude}`;
      const dest = `${destination.lat},${destination.lng}`;
      const url = `https://maps.googleapis.com/maps/api/directions/json?origin=${origin}&destination=${dest}&key=${GOOGLE_MAPS_API_KEY}`;
      const res = await fetch(url);
      const json = await res.json();
      if (json.status === "OK" && json.routes.length > 0) {
        const points = decodePolyline(json.routes[0].overview_polyline.points);
        setPath(points);
        const leg = json.routes[0].legs[0];
        setRouteInfo({ distance: leg.distance.text, duration: leg.duration.text });
        if (mapRef.current) {
          mapRef.current.fitToCoordinates(points, {
            edgePadding: { top: 50, right: 50, bottom: 250, left: 50 },
            animated: true,
          });
        }
      }
    } catch (err) {
      console.error("[RideTracking] Route fetch failed:", err);
    }
  }

  // ── GPS state (persists between renders via refs) ─────────────────
  const prevGpsRef = useRef<{ lat: number; lng: number; ts: number } | null>(null);
  const kmTraveledRef = useRef<number>(0);
  const keepAliveRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** Haversine distance in meters between two GPS points */
  function haversineMeters(lat1: number, lng1: number, lat2: number, lng2: number) {
    const R = 6371000;
    const φ1 = (lat1 * Math.PI) / 180, φ2 = (lat2 * Math.PI) / 180;
    const Δφ = ((lat2 - lat1) * Math.PI) / 180;
    const Δλ = ((lng2 - lng1) * Math.PI) / 180;
    const a = Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  /** Bearing between two GPS points (degrees) */
  function computeBearing(lat1: number, lng1: number, lat2: number, lng2: number) {
    const dLon = ((lng2 - lng1) * Math.PI) / 180;
    const y = Math.sin(dLon) * Math.cos((lat2 * Math.PI) / 180);
    const x =
      Math.cos((lat1 * Math.PI) / 180) * Math.sin((lat2 * Math.PI) / 180) -
      Math.sin((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.cos(dLon);
    return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
  }

  async function startLocationBroadcast() {
    await connectLocationSocket();

    // 📡 Keep-alive ping every 20 seconds so WS doesn't time out silently
    keepAliveRef.current = setInterval(() => {
      sendLocation(
        prevGpsRef.current?.lat ?? 0,
        prevGpsRef.current?.lng ?? 0,
        null
      );
    }, 20000);

    await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.BestForNavigation,
        distanceInterval: 3,      // min 3 m movement before update
        timeInterval: 3000,       // max 3 s between updates
      },
      (loc) => {
        const { latitude: lat, longitude: lng, accuracy, heading, speed } = loc.coords;

        // 🚫 Reject noisy GPS readings (accuracy worse than 40 m)
        if (accuracy !== null && accuracy > 40) {
          console.warn(`[GPS] Low accuracy: ${accuracy.toFixed(0)} m — skipping`);
          return;
        }

        const now = Date.now();
        const prev = prevGpsRef.current;

        // Calculate derived values from movement delta
        let computedHeading = heading;
        let computedSpeedKmh = speed !== null ? speed * 3.6 : 0;
        let distDelta = 0;

        if (prev) {
          distDelta = haversineMeters(prev.lat, prev.lng, lat, lng);
          const timeDeltaSec = (now - prev.ts) / 1000;

          // Fallback heading from consecutive points (device may not supply it)
          if ((computedHeading === null || computedHeading < 0) && distDelta > 2) {
            computedHeading = computeBearing(prev.lat, prev.lng, lat, lng);
          }

          // Fallback speed if expo doesn't supply it
          if (speed === null && timeDeltaSec > 0) {
            computedSpeedKmh = (distDelta / timeDeltaSec) * 3.6;
          }

          // Accumulate distance traveled
          if (distDelta > 1) {
            kmTraveledRef.current += distDelta / 1000;
          }
        }

        prevGpsRef.current = { lat, lng, ts: now };
        setCurrentLocation(loc.coords);

        // 📤 Send to backend with enriched payload
        sendLocation(lat, lng, computedHeading ?? null, computedSpeedKmh, accuracy ?? null);

        console.log(
          `[GPS] 📍 (${lat.toFixed(5)}, ${lng.toFixed(5)}) | ` +
          `acc=${accuracy?.toFixed(0)}m | hdg=${computedHeading?.toFixed(0)}° | ` +
          `spd=${computedSpeedKmh.toFixed(1)}km/h | dist=${distDelta.toFixed(1)}m | ` +
          `total=${kmTraveledRef.current.toFixed(2)}km`
        );

        if (mapRef.current) {
          mapRef.current.animateToRegion({
            latitude: lat,
            longitude: lng,
            latitudeDelta: 0.01,
            longitudeDelta: 0.01,
          }, 800);
        }
      }
    );
  }

  async function fetchRideDetails() {
    try {
      const { data } = await api.get(`rides/${rideId}/`);
      setRideData(data);
      setRideStatus(data.status);
      if (data.planned_route_polyline) {
        setPath(decodePolyline(data.planned_route_polyline));
      }
    } catch (err) {
      console.error("[RideTracking] Failed to fetch ride details");
    }
  }

  async function markArrived() {
    try {
      await api.post(`rides/${rideId}/arrived/`);
      setRideStatus("ARRIVED");
    } catch (err: any) {
      Alert.alert("Error", err.response?.data?.error || "Failed to mark arrived");
    }
  }

  async function startRide() {
    if (!otp) {
      Alert.alert("Error", "Please enter OTP");
      return;
    }
    try {
      await api.post(`rides/${rideId}/start/`, { otp });
      setRideStatus("ONGOING");
    } catch (err: any) {
      Alert.alert("Error", err.response?.data?.error || "Invalid OTP");
    }
  }

  async function completeRide() {
    try {
      if (locationIntervalRef.current) clearInterval(locationIntervalRef.current);
      await api.post(`rides/${rideId}/complete/`);
      setShowRating(true);
    } catch (err: any) {
      Alert.alert("Error", err.response?.data?.error || "Failed to complete ride");
    }
  }

  async function submitRating() {
    if (!rating) {
      Alert.alert("Error", "Please select a rating");
      return;
    }
    try {
      await api.post(`rides/${rideId}/feedback/`, { rating, comment });
      Alert.alert("Success", "Rating submitted!");
      navigation.replace("Home");
    } catch (err: any) {
      Alert.alert("Error", "Failed to submit rating");
      navigation.replace("Home");
    }
  }

  const pickup = rideData ? { lat: rideData.pickup_lat, lng: rideData.pickup_lng } : null;
  const dropoff = rideData ? { lat: rideData.drop_lat, lng: rideData.drop_lng } : null;

  return (
    <View style={styles.container}>
      <View style={styles.mapContainer}>
        <MapView
          ref={mapRef}
          provider={PROVIDER_GOOGLE}
          style={styles.map}
          initialRegion={{
            latitude: currentLocation?.latitude || pickup?.lat || 13.0827,
            longitude: currentLocation?.longitude || pickup?.lng || 80.2707,
            latitudeDelta: 0.01,
            longitudeDelta: 0.01,
          }}
          showsUserLocation={false}
          followsUserLocation={false}
        >
          {currentLocation && (
            <Marker
              coordinate={{
                latitude: currentLocation.latitude,
                longitude: currentLocation.longitude,
              }}
              anchor={{ x: 0.5, y: 0.5 }}
              flat
              rotation={currentLocation.heading || 0}
            >
              <Image
                source={{ uri: "https://cdn-icons-png.flaticon.com/512/853/853961.png" }}
                style={{ width: 40, height: 40 }}
              />
            </Marker>
          )}
          {path.length > 0 && (
            <Polyline coordinates={path} strokeWidth={4} strokeColor="#2563eb" />
          )}
          {pickup && (
            <Marker coordinate={{ latitude: pickup.lat, longitude: pickup.lng }} title="Pickup" pinColor="green" />
          )}
          {dropoff && (
            <Marker coordinate={{ latitude: dropoff.lat, longitude: dropoff.lng }} title="Dropoff" pinColor="red" />
          )}
        </MapView>
      </View>

      <View style={styles.controls}>
        <View style={styles.header}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: "#f3f4f6", justifyContent: "center", alignItems: "center", overflow: "hidden" }}>
              <Image
                source={{
                  uri: rideData?.vehicle_type === "moto" ? "https://cn-geo1.uber.com/image-proc/resize/e_sharpen:20/q_auto:eco/width_270/v1/product_icons/6f31623d-2495-4677-9a80-e83cb2b00194.png" :
                    rideData?.vehicle_type === "auto" ? "https://cn-geo1.uber.com/image-proc/resize/e_sharpen:20/q_auto:eco/width_270/v1/product_icons/74836f6e-5494-4bb8-88e8-97ef91136934.png" :
                      rideData?.vehicle_type === "xl" ? "https://cn-geo1.uber.com/image-proc/resize/e_sharpen:20/q_auto:eco/width_270/v1/product_icons/5f5ec280-9289-4e1c-bb5b-3a45c61a551b.png" :
                        "https://cn-geo1.uber.com/image-proc/resize/e_sharpen:20/q_auto:eco/width_270/v1/product_icons/f622915c-097b-4043-b67e-39908cfcb1e7.png"
                }}
                style={{ width: "90%", height: "90%", resizeMode: "contain" }}
              />
            </View>
            <Text style={styles.title}>Ride #{rideId}</Text>
          </View>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <TouchableOpacity onPress={triggerSOS} style={styles.sosCircle}>
              <Text style={{ color: "#fff", fontWeight: "bold", fontSize: 10 }}>SOS</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => navigation.navigate("CreateSupport", { rideId })} style={styles.helpCircle}>
              <Text style={{ color: "#fff", fontWeight: "bold", fontSize: 10 }}>Help</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setChatOpen(true)} style={styles.chatBadge}>
              <Text style={{ color: "#fff", fontWeight: "bold" }}>💬</Text>
              {messages.length > 0 && <View style={styles.redDot} />}
            </TouchableOpacity>
            <View style={[styles.statusBadge, statusColor(rideStatus)]}>
              <Text style={styles.statusText}>{rideStatus}</Text>
            </View>
          </View>
        </View>

        {routeInfo.distance ? (
          <View style={styles.routeHeader}>
            <Text style={styles.routeStat}>📏 {routeInfo.distance}</Text>
            <Text style={styles.routeStat}>⏱️ {routeInfo.duration}</Text>
          </View>
        ) : null}

        <View style={styles.addressContainer}>
          <Text style={styles.addressLabel}>
            {rideStatus === "ASSIGNED" ? "PICKUP FROM" : rideStatus === "ONGOING" ? "DROP AT" : "LOCATION"}
          </Text>
          <Text style={styles.addressText} numberOfLines={2}>
            {rideStatus === "ASSIGNED"
              ? (rideData?.pickup_address && rideData.pickup_address !== "Pickup Point"
                ? rideData.pickup_address
                : `${rideData?.pickup_lat?.toFixed(5)}, ${rideData?.pickup_lng?.toFixed(5)}`)
              : (rideData?.drop_address && rideData.drop_address !== "Destination"
                ? rideData.drop_address
                : `${rideData?.drop_lat?.toFixed(5)}, ${rideData?.drop_lng?.toFixed(5)}`)
            }
          </Text>
        </View>

        <View style={styles.card}>
          {rideStatus === "ASSIGNED" && (
            <TouchableOpacity style={styles.btn} onPress={markArrived}>
              <Text style={styles.btnText}>Mark as Arrived</Text>
            </TouchableOpacity>
          )}
          {rideStatus === "ARRIVED" && (
            <>
              <TextInput
                style={styles.input}
                placeholder="Enter OTP"
                value={otp}
                onChangeText={setOtp}
                keyboardType="number-pad"
                maxLength={6}
              />
              <TouchableOpacity style={styles.btn} onPress={startRide}>
                <Text style={styles.btnText}>Start Ride</Text>
              </TouchableOpacity>
            </>
          )}
          {rideStatus === "ONGOING" && (
            <TouchableOpacity style={styles.btn} onPress={completeRide}>
              <Text style={styles.btnText}>Complete Ride</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {chatOpen && (
        <View style={styles.chatModal}>
          <View style={styles.chatHeader}>
            <Text style={{ fontWeight: "bold" }}>Chat with Rider</Text>
            <TouchableOpacity onPress={() => setChatOpen(false)}>
              <Text style={{ color: "red", fontWeight: "bold" }}>Close</Text>
            </TouchableOpacity>
          </View>
          <View style={{ flex: 1, padding: 10 }}>
            {messages.map((m, i) => (
              <View key={i} style={m.sender_id === rideData?.driver?.user_id ? styles.myMsg : styles.theirMsg}>
                <Text style={{ color: m.sender_id === rideData?.driver?.user_id ? "#fff" : "#000" }}>{m.message}</Text>
              </View>
            ))}
          </View>
          <View style={styles.chatInputRow}>
            <TextInput style={styles.chatInput} value={msgInput} onChangeText={setMsgInput} placeholder="Type a message..." />
            <TouchableOpacity style={styles.sendBtn} onPress={() => { sendRideChat(msgInput); setMsgInput(""); }}>
              <Text style={{ color: "#fff", fontWeight: "bold" }}>Send</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {showRating && (
        <View style={styles.ratingOverlay}>
          <View style={styles.ratingCard}>
            <Text style={styles.ratingTitle}>Rate your Rider</Text>
            <View style={styles.starsRow}>
              {[1, 2, 3, 4, 5].map((num) => (
                <TouchableOpacity key={num} onPress={() => setRating(num)}>
                  <Text style={[styles.star, rating >= num && styles.starActive]}>★</Text>
                </TouchableOpacity>
              ))}
            </View>
            <TextInput
              style={styles.ratingInput}
              placeholder="How was the rider? (Optional)"
              value={comment}
              onChangeText={setComment}
              multiline
            />
            <TouchableOpacity style={styles.submitBtn} onPress={submitRating}>
              <Text style={styles.submitBtnText}>Submit Rating</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => navigation.replace("Home")}>
              <Text style={styles.skipText}>Skip</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

function statusColor(status: string): object {
  const colors: Record<string, string> = {
    ASSIGNED: "#007AFF",
    ARRIVED: "#FF9500",
    ONGOING: "#34C759",
  };
  return { backgroundColor: colors[status] || "#8E8E93" };
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020408" },
  mapContainer: { flex: 1 },
  map: { ...StyleSheet.absoluteFillObject },
  controls: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    backgroundColor: "rgba(15,23,42,0.9)",
    borderTopLeftRadius: 36,
    borderTopRightRadius: 36,
    padding: 28,
    paddingBottom: 48,
    borderTopWidth: 1, // dummy for consistency
    borderColor: "rgba(255,255,255,0.1)",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: -20 },
    shadowOpacity: 0.5,
    shadowRadius: 40,
    elevation: 20,
  },
  header: {
    marginBottom: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center"
  },
  title: { fontSize: 22, fontWeight: "800", color: "#f8fafc", letterSpacing: -0.5 },
  statusBadge: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)"
  },
  statusText: { color: "#fff", fontSize: 11, fontWeight: "900", textTransform: "uppercase", letterSpacing: 1 },
  routeHeader: {
    flexDirection: "row",
    gap: 16,
    backgroundColor: "rgba(39,110,241,0.1)",
    padding: 14,
    borderRadius: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "rgba(39,110,241,0.2)",
  },
  routeStat: {
    fontSize: 14,
    fontWeight: "800",
    color: "#3b82f6",
  },
  card: { gap: 16 },
  addressContainer: { marginBottom: 24, paddingHorizontal: 4 },
  addressLabel: {
    color: "#64748b",
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.5,
    textTransform: "uppercase",
    marginBottom: 8
  },
  addressText: { fontSize: 20, fontWeight: "800", color: "#f1f5f9", lineHeight: 26, letterSpacing: -0.3 },
  btn: {
    backgroundColor: "#276EF1",
    padding: 20,
    borderRadius: 20,
    alignItems: "center",
    shadowColor: "#276EF1",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
  },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "900", textTransform: "uppercase", letterSpacing: 1 },
  input: {
    backgroundColor: "rgba(255,255,255,0.03)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    padding: 20,
    borderRadius: 16,
    textAlign: "center",
    fontSize: 28,
    letterSpacing: 20,
    color: "#34C759",
    fontWeight: "900",
    marginBottom: 16
  },
  sosCircle: {
    backgroundColor: "rgba(239, 68, 68, 0.15)",
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.3)"
  },
  helpCircle: {
    backgroundColor: "rgba(255,255,255,0.05)",
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)"
  },
  chatBadge: {
    backgroundColor: "rgba(39, 110, 241, 0.15)",
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
    borderWidth: 1,
    borderColor: "rgba(39, 110, 241, 0.3)"
  },
  redDot: {
    position: "absolute",
    top: 2,
    right: 2,
    backgroundColor: "#ef4444",
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: "#020408"
  },
  chatModal: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    height: "100%",
    backgroundColor: "#020408",
    zIndex: 5000
  },
  chatHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 24,
    paddingTop: 64,
    borderBottomWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    backgroundColor: "rgba(15,23,42,0.95)"
  },
  myMsg: {
    backgroundColor: "#276EF1",
    padding: 16,
    borderRadius: 20,
    alignSelf: "flex-end",
    marginBottom: 12,
    maxWidth: "85%",
    borderBottomRightRadius: 4
  },
  theirMsg: {
    backgroundColor: "rgba(255,255,255,0.06)",
    padding: 16,
    borderRadius: 20,
    alignSelf: "flex-start",
    marginBottom: 12,
    maxWidth: "85%",
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.05)"
  },
  chatInputRow: {
    flexDirection: "row",
    padding: 20,
    paddingBottom: 48,
    borderTopWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    backgroundColor: "rgba(15,23,42,0.98)",
    alignItems: "center",
    gap: 16
  },
  chatInput: {
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.04)",
    paddingHorizontal: 20,
    borderRadius: 28,
    height: 52,
    color: "#f8fafc",
    fontSize: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)"
  },
  sendBtn: {
    backgroundColor: "#276EF1",
    width: 52,
    height: 52,
    borderRadius: 26,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#276EF1",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8
  },
  ratingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(2,4,8,0.95)",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 10000
  },
  ratingCard: {
    backgroundColor: "rgba(15,23,42,0.8)",
    width: "90%",
    padding: 32,
    borderRadius: 32,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)"
  },
  ratingTitle: { fontSize: 24, fontWeight: "900", marginBottom: 24, color: "#f8fafc" },
  starsRow: { flexDirection: "row", gap: 12, marginBottom: 32 },
  star: { fontSize: 44, color: "rgba(255,255,255,0.1)" },
  starActive: { color: "#fbbf24" },
  ratingInput: {
    width: "100%",
    height: 100,
    backgroundColor: "rgba(255,255,255,0.03)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    borderRadius: 20,
    padding: 16,
    marginBottom: 32,
    textAlignVertical: "top",
    color: "#f1f5f9",
    fontSize: 15
  },
  submitBtn: {
    backgroundColor: "#276EF1",
    width: "100%",
    padding: 20,
    borderRadius: 20,
    alignItems: "center",
    marginBottom: 20,
    shadowColor: "#276EF1",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 15
  },
  submitBtnText: { color: "#fff", fontSize: 16, fontWeight: "900", textTransform: "uppercase", letterSpacing: 1 },
  skipText: { color: "#64748b", fontSize: 14, fontWeight: "700" }
});
