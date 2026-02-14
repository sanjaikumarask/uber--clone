import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, Switch } from "react-native";
import { useAuthStore } from "../domains/auth/auth.store";
import { api } from "../services/api";
import * as Location from "expo-location";

export default function HomeScreen({ navigation }: any) {
    const { user, logout } = useAuthStore();
    const [isOnline, setIsOnline] = useState(false);
    const [location, setLocation] = useState<any>(null);

    useEffect(() => {
        requestLocationPermission();
    }, []);

    useEffect(() => {
        if (isOnline && location) {
            const interval = setInterval(() => {
                updateLocation();
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [isOnline, location]);

    async function requestLocationPermission() {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== "granted") {
            Alert.alert("Permission Denied", "Location permission is required");
            return;
        }
        const loc = await Location.getCurrentPositionAsync({});
        setLocation(loc);
    }

    async function updateLocation() {
        try {
            const loc = await Location.getCurrentPositionAsync({});
            setLocation(loc);
            await api.post("/tracking/update-location/", {
                lat: loc.coords.latitude,
                lng: loc.coords.longitude,
            });
            console.log("✅ Location updated successfully");
        } catch (err: any) {
            console.error("❌ Failed to update location", err);
            if (err.response?.status === 401) {
                console.error("❌ Token expired - logging out");
                Alert.alert("Session Expired", "Please login again");
                await logout();
            }
        }
    }

    async function toggleOnlineStatus() {
        try {
            const newStatus = !isOnline;
            console.log(`🔄 Updating status to: ${newStatus ? 'ONLINE' : 'OFFLINE'}`);

            await api.post("/drivers/status/", {
                status: newStatus ? "ONLINE" : "OFFLINE",
            });

            console.log("✅ Status updated successfully");
            setIsOnline(newStatus);

            if (newStatus) {
                updateLocation();
            }
        } catch (err: any) {
            console.error("❌ Failed to update status", err);
            console.error("❌ Error response:", err.response?.data);
            console.error("❌ Error status:", err.response?.status);

            const errorMsg = err.response?.data?.error
                || err.response?.data?.detail
                || "Failed to update status";

            Alert.alert("Error", errorMsg);
        }
    }

    async function handleLogout() {
        await logout();
    }

    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <Text style={styles.title}>Driver Dashboard</Text>
                <TouchableOpacity onPress={handleLogout}>
                    <Text style={styles.logoutText}>Logout</Text>
                </TouchableOpacity>
            </View>

            <View style={styles.card}>
                <Text style={styles.welcomeText}>
                    Welcome, {user?.first_name || "Driver"}!
                </Text>
                <Text style={styles.phoneText}>{user?.phone}</Text>
            </View>

            <View style={styles.card}>
                <View style={styles.statusRow}>
                    <Text style={styles.statusLabel}>Status:</Text>
                    <View style={styles.statusToggle}>
                        <Text style={styles.statusText}>{isOnline ? "ONLINE" : "OFFLINE"}</Text>
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
                <TouchableOpacity
                    style={styles.actionButton}
                    onPress={() => navigation.navigate("Wallet")}
                >
                    <Text style={styles.actionButtonText}>💰 Wallet</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={styles.actionButton}
                    onPress={() => navigation.navigate("Notifications")}
                >
                    <Text style={styles.actionButtonText}>🔔 Notifications</Text>
                </TouchableOpacity>
            </View>

            <View style={styles.infoCard}>
                <Text style={styles.infoText}>
                    {isOnline
                        ? "You are online and ready to receive ride requests!"
                        : "Go online to start receiving ride requests"}
                </Text>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#f5f5f5",
        padding: 20,
        paddingTop: 60,
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 30,
    },
    title: {
        fontSize: 24,
        fontWeight: "bold",
    },
    logoutText: {
        color: "#007AFF",
        fontSize: 16,
    },
    card: {
        backgroundColor: "#fff",
        padding: 20,
        borderRadius: 12,
        marginBottom: 15,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    welcomeText: {
        fontSize: 20,
        fontWeight: "600",
        marginBottom: 5,
    },
    phoneText: {
        fontSize: 16,
        color: "#666",
    },
    statusRow: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
    },
    statusLabel: {
        fontSize: 18,
        fontWeight: "600",
    },
    statusToggle: {
        flexDirection: "row",
        alignItems: "center",
        gap: 10,
    },
    statusText: {
        fontSize: 16,
        fontWeight: "600",
        color: "#007AFF",
    },
    locationTitle: {
        fontSize: 16,
        fontWeight: "600",
        marginBottom: 10,
    },
    locationText: {
        fontSize: 14,
        color: "#666",
        marginBottom: 5,
    },
    actionsRow: {
        flexDirection: "row",
        gap: 10,
        marginBottom: 15,
    },
    actionButton: {
        flex: 1,
        backgroundColor: "#fff",
        padding: 15,
        borderRadius: 12,
        alignItems: "center",
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    actionButtonText: {
        fontSize: 16,
        fontWeight: "600",
    },
    infoCard: {
        backgroundColor: "#E3F2FD",
        padding: 20,
        borderRadius: 12,
        marginTop: 10,
    },
    infoText: {
        fontSize: 14,
        color: "#1976D2",
        textAlign: "center",
    },
});
