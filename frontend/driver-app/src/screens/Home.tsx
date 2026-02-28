// src/screens/Home.tsx (driver-app)

import React, { useState, useEffect, useRef, useCallback } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, Switch } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useAuthStore } from "../domains/auth/auth.store";
import { api } from "../services/api";
import * as Location from "expo-location";
import {
  connectLocationSocket,
  disconnectLocationSocket,
  sendLocation,
  connectRidesSocket,
  disconnectRidesSocket,
  onRidesEvent,
} from "../services/socket";

export default function HomeScreen({ navigation }: any) {
  const { user, logout, syncUser } = useAuthStore();
  const [isOnline, setIsOnline] = useState(false);

  useFocusEffect(
    useCallback(() => {
      syncUser();
    }, [])
  );
  const [location, setLocation] = useState<Location.LocationObject | null>(null);
  const locationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function requestLocationPermission() {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission Denied", "Location permission is required to receive ride requests.");
        return;
      }
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setLocation(loc);
    } catch (e) {
      console.warn("Failed to get initial location", e);
    }
  }

  useEffect(() => {
    requestLocationPermission();
    connectRidesSocket();
    checkForActiveRide();

    const unsubOffer = onRidesEvent("ride_offer", (payload) => {
      navigation.navigate("RideOffer", { offer: payload.data });
    });

    const unsubAssigned = onRidesEvent("ride_assigned", (payload) => {
      // Navigate to RideOffer with all details — driver sees pickup/drop/fare
      // isAutoAssigned=true hides Accept/Reject and shows a countdown instead
      navigation.navigate("RideOffer", { offer: { ...payload.data, is_auto_assigned: true } });
    });

    const unsubFeedback = onRidesEvent("DRIVER_FEEDBACK", (payload) => {
      Alert.alert(payload.data.title || "Performance Feedback", payload.data.message);
    });

    const unsubLevel = onRidesEvent("LEVEL_CHANGED", (payload) => {
      Alert.alert("Level Updated!", payload.data.message);
    });

    const unsubSuspension = onRidesEvent("ACCOUNT_SUSPENDED", (payload) => {
      Alert.alert("Account Restricted", payload.data.message);
      setIsOnline(false);
    });

    return () => {
      unsubOffer();
      unsubAssigned();
      unsubFeedback();
      unsubLevel();
      unsubSuspension();
      disconnectRidesSocket();
      disconnectLocationSocket();
      if (locationIntervalRef.current) clearInterval(locationIntervalRef.current);
    };
  }, []);

  async function checkForActiveRide() {
    try {
      const { data } = await api.get("/drivers/active-ride/");
      if (data && data.status) {
        setIsOnline(true);
        navigation.replace("RideTracking", { rideId: data.id });
      } else {
        const profile = await api.get("/drivers/me/");
        setIsOnline(profile.data.status === "ONLINE");
      }
    } catch (err) {
      console.log("[Home] No active ride found or profile fetch failed");
    }
  }

  useEffect(() => {
    if (isOnline) {
      connectLocationSocket();
      locationIntervalRef.current = setInterval(broadcastLocation, 3000);
    } else {
      if (locationIntervalRef.current) {
        clearInterval(locationIntervalRef.current);
        locationIntervalRef.current = null;
      }
      disconnectLocationSocket();
    }

    return () => {
      if (locationIntervalRef.current) {
        clearInterval(locationIntervalRef.current);
        locationIntervalRef.current = null;
      }
    };
  }, [isOnline]);

  async function broadcastLocation() {
    try {
      const { status } = await Location.getForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.warn("[Home] Cannot broadcast: Location permission not granted.");
        setIsOnline(false); // Force them offline if GPS fails
        return;
      }

      const servicesEnabled = await Location.hasServicesEnabledAsync();
      if (!servicesEnabled) {
        console.warn("[Home] Location services are disabled at OS level.");
        Alert.alert("GPS Disabled", "Please enable Location Services in your phone settings to receive rides.");
        setIsOnline(false);
        return;
      }

      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced, // Use Balanced instead of Highest to prevent hardware timeouts
      });
      setLocation(loc);
      sendLocation(loc.coords.latitude, loc.coords.longitude, loc.coords.heading);
    } catch (err: any) {
      // Give a softer alert so it doesn't spam infinitely every 3 seconds
      const errMsg = err?.message?.toLowerCase() || "";
      if (errMsg.includes("location is unavailable")) {
        // 🚨 PHYSICAL DEVICE FIX: GPS signal bouncing is normal.
        // Don't kick the driver offline or show an alert, just wait 3 seconds and try again.
        console.warn("[Home] GPS signal temporarily lost. Waiting for next ping...");
        return;
      }

      console.error("[Home] Failed to get/send location:", err);

      if (errMsg.includes("location services are disabled") || errMsg.includes("location services are enabled")) {
        Alert.alert("GPS Error", "We could not find your location. Please check your phone settings.");
        setIsOnline(false); // Stop the 3-second loop
      } else if (err?.response?.status === 401) {
        Alert.alert("Session Expired", "Please login again");
        await logout();
      }
    }
  }

  async function toggleOnlineStatus() {
    if (!user?.is_verified) {
      Alert.alert("Action Blocked", "Please upload documents and get verified before going online.");
      return;
    }
    try {
      const newStatus = !isOnline;
      await api.post("/drivers/status/", {
        status: newStatus ? "ONLINE" : "OFFLINE",
      });
      setIsOnline(newStatus);
      if (newStatus) broadcastLocation();
    } catch (err: any) {
      const msg = err.response?.data?.error
        || err.response?.data?.detail
        || "Failed to update status";
      Alert.alert("Error", msg);
    }
  }

  async function handleLogout() {
    disconnectLocationSocket();
    disconnectRidesSocket();
    await logout();
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Driver Dashboard</Text>
        <View style={{ flexDirection: "row", gap: 15 }}>
          <TouchableOpacity onPress={syncUser}>
            <Text style={styles.syncText}>🔄 Sync</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleLogout}>
            <Text style={styles.logoutText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.welcomeText}>Welcome, {user?.first_name || "Driver"}!</Text>
        <Text style={styles.phoneText}>{user?.phone}</Text>
      </View>

      {/* DEBUG: Remove this in production */}
      <View style={{ padding: 10, backgroundColor: "#eee", borderRadius: 8, marginBottom: 10 }}>
        <Text style={{ fontSize: 12 }}>Debug | Role: {user?.role} | Verified: {String(user?.is_verified)}</Text>
      </View>

      {(user?.role === "driver" && user?.is_verified === false) ? (
        <TouchableOpacity
          style={styles.verificationBanner}
          onPress={() => navigation.navigate("DocumentUpload")}
        >
          <Text style={styles.bannerEmoji}>📝</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.bannerTitle}>Verification Required</Text>
            <Text style={styles.bannerSubtitle}>Upload Documents to start riding</Text>
          </View>
          <Text style={styles.bannerArrow}>→</Text>
        </TouchableOpacity>
      ) : (user?.role === "rider") ? (
        <View style={[styles.verificationBanner, { backgroundColor: "#FFFBEB", borderColor: "#FDE68A" }]}>
          <Text style={styles.bannerEmoji}>⚠️</Text>
          <View style={{ flex: 1 }}>
            <Text style={[styles.bannerTitle, { color: "#92400E" }]}>Rider Account Detected</Text>
            <Text style={[styles.bannerSubtitle, { color: "#92400E" }]}>Please register as a driver to use this app.</Text>
          </View>
        </View>
      ) : null}

      <View style={styles.card}>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Status:</Text>
          <View style={styles.statusToggle}>
            <Text style={[styles.statusText, { color: isOnline ? "#34C759" : "#8E8E93" }]}>
              {isOnline ? "ONLINE" : "OFFLINE"}
            </Text>
            <Switch value={isOnline} onValueChange={toggleOnlineStatus} />
          </View>
        </View>
      </View>

      {location && (
        <View style={styles.card}>
          <Text style={styles.locationTitle}>Current Location</Text>
          <Text style={styles.locationText}>
            Lat: {location.coords.latitude.toFixed(6)}
          </Text>
          <Text style={styles.locationText}>
            Lng: {location.coords.longitude.toFixed(6)}
          </Text>
        </View>
      )}

      <View style={styles.actionsRow}>
        <TouchableOpacity style={styles.actionButton} onPress={() => navigation.navigate("Wallet")}>
          <Text style={styles.actionButtonText}>💰 Wallet</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton} onPress={() => navigation.navigate("Notifications")}>
          <Text style={styles.actionButtonText}>🔔 Notifications</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton} onPress={() => navigation.navigate("Incentives")}>
          <Text style={styles.actionButtonText}>🎁 Gift</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton} onPress={() => navigation.navigate("Support")}>
          <Text style={styles.actionButtonText}>🎧 Help</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.infoText}>
          {isOnline
            ? "📡 Broadcasting location — ready for ride requests!"
            : "Go online to start receiving ride requests"}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5", padding: 20, paddingTop: 60 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 30 },
  title: { fontSize: 24, fontWeight: "bold" },
  logoutText: { color: "#007AFF", fontSize: 16 },
  syncText: { color: "#34C759", fontSize: 16, fontWeight: "600" },
  card: { backgroundColor: "#fff", padding: 20, borderRadius: 12, marginBottom: 15, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  welcomeText: { fontSize: 20, fontWeight: "600", marginBottom: 5 },
  phoneText: { fontSize: 16, color: "#666" },
  statusRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  statusLabel: { fontSize: 18, fontWeight: "600" },
  statusToggle: { flexDirection: "row", alignItems: "center", gap: 10 },
  statusText: { fontSize: 16, fontWeight: "600" },
  locationTitle: { fontSize: 16, fontWeight: "600", marginBottom: 10 },
  locationText: { fontSize: 14, color: "#666", marginBottom: 5 },
  actionsRow: { flexDirection: "row", gap: 10, marginBottom: 15 },
  actionButton: { flex: 1, backgroundColor: "#fff", padding: 10, borderRadius: 12, alignItems: "center", shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  actionButtonText: { fontSize: 13, fontWeight: "600" },
  infoCard: { backgroundColor: "#E3F2FD", padding: 20, borderRadius: 12, marginTop: 10 },
  infoText: { fontSize: 14, color: "#1976D2", textAlign: "center" },
  verificationBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FDF2F2",
    padding: 15,
    borderRadius: 12,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "#FBD5D5",
    gap: 12,
  },
  bannerEmoji: { fontSize: 24 },
  bannerTitle: { fontSize: 16, fontWeight: "700", color: "#9B1C1C" },
  bannerSubtitle: { fontSize: 13, color: "#9B1C1C", opacity: 0.8 },
  bannerArrow: { fontSize: 18, fontWeight: "700", color: "#9B1C1C" },
});