import React, { useEffect, useRef, useState } from "react";
import {
    View, Text, StyleSheet, TouchableOpacity, Alert,
    Animated, Easing, Dimensions, StatusBar
} from "react-native";
import { api, WS_URL } from "../services/api";
import { Storage } from "../services/storage";

const { width } = Dimensions.get("window");

const VEHICLE_LABELS: Record<string, { emoji: string; name: string }> = {
    moto: { emoji: "🏍️", name: "Uber Moto" },
    auto: { emoji: "🛺", name: "Uber Auto" },
    go: { emoji: "🚗", name: "UberGo" },
    xl: { emoji: "🚙", name: "UberXL" },
};

export default function RideSearchingScreen({ navigation, route }: any) {
    const { rideId, vehicleType = "go" } = route.params;
    const [status, setStatus] = useState("SEARCHING");
    const vehicle = VEHICLE_LABELS[vehicleType] || VEHICLE_LABELS.go;

    // ── Animated rings ──
    const ring1 = useRef(new Animated.Value(0)).current;
    const ring2 = useRef(new Animated.Value(0)).current;
    const ring3 = useRef(new Animated.Value(0)).current;

    const pulse = (anim: Animated.Value, delay: number) =>
        Animated.loop(
            Animated.sequence([
                Animated.delay(delay),
                Animated.timing(anim, {
                    toValue: 1,
                    duration: 2000,
                    easing: Easing.out(Easing.ease),
                    useNativeDriver: true,
                }),
                Animated.timing(anim, {
                    toValue: 0,
                    duration: 0,
                    useNativeDriver: true,
                }),
            ])
        );

    useEffect(() => {
        const a1 = pulse(ring1, 0);
        const a2 = pulse(ring2, 600);
        const a3 = pulse(ring3, 1200);
        a1.start(); a2.start(); a3.start();
        return () => { a1.stop(); a2.stop(); a3.stop(); };
    }, []);

    // ── Dot spinner ──
    const dotAnim = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.loop(
            Animated.sequence([
                Animated.timing(dotAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
                Animated.timing(dotAnim, { toValue: 0, duration: 800, useNativeDriver: true }),
            ])
        ).start();
    }, []);

    // ── WebSocket ──
    useEffect(() => {
        let ws: WebSocket | null = null;
        const setup = async () => {
            try {
                const res = await api.get(`/rides/${rideId}/`);
                const s = res.data.status;
                if (["ASSIGNED", "ARRIVED", "ONGOING"].includes(s)) {
                    navigation.replace("RideTracking", { rideId });
                    return;
                }
                if (s === "COMPLETED") {
                    navigation.replace("RideCompletion", { rideId });
                    return;
                }
                if (s === "CANCELLED") {
                    navigation.replace("Home");
                    return;
                }
                setStatus(s);
            } catch (err) {
                console.error("Ride fetch failed", err);
            }

            const token = await Storage.getToken();
            if (!token) return;

            ws = new WebSocket(`${WS_URL}/rides/${rideId}/?token=${token}`);
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                // Handle both generic update and specific status update
                if (data.type === "ride_update" || data.type === "RIDE_STATUS_UPDATED") {
                    const rideData = data.payload?.ride || data.ride || data.payload;
                    if (rideData) {
                        setStatus(rideData.status);
                        if (["ASSIGNED", "ARRIVED", "ONGOING"].includes(rideData.status)) {
                            navigation.replace("RideTracking", { rideId });
                        } else if (rideData.status === "COMPLETED") {
                            navigation.replace("RideCompletion", { rideId });
                        } else if (rideData.status === "CANCELLED") {
                            navigation.replace("Home");
                        }
                    }
                }
            };
        };
        setup();
        return () => { if (ws) ws.close(); };
    }, [rideId]);

    const handleCancel = async () => {
        try {
            await api.post(`/rides/${rideId}/cancel/`);
            navigation.replace("Home");
        } catch {
            Alert.alert("Error", "Failed to cancel ride.");
        }
    };

    const ringStyle = (anim: Animated.Value) => ({
        transform: [{
            scale: anim.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1.8] }),
        }],
        opacity: anim.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0.8, 0.3, 0] }),
    });

    const statusLabel = status === "OFFERED" ? "Confirming..." : "Searching nearby...";
    const statusColor = status === "OFFERED" ? "#22c55e" : "#276EF1";

    return (
        <View style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor="#000" />

            {/* ── Radar Zone ── */}
            <View style={styles.radarZone}>
                {/* Animated rings */}
                <Animated.View style={[styles.ring, ringStyle(ring1)]} />
                <Animated.View style={[styles.ring, ringStyle(ring2)]} />
                <Animated.View style={[styles.ring, ringStyle(ring3)]} />

                {/* Vehicle icon in centre */}
                <View style={styles.vehicleCircle}>
                    <Text style={styles.vehicleEmoji}>{vehicle.emoji}</Text>
                </View>
            </View>

            {/* ── Info ── */}
            <View style={styles.infoZone}>
                <Text style={styles.title}>Finding your{"\n"}{vehicle.name}</Text>
                <Text style={styles.subtitle}>Matching you with a nearby driver...</Text>

                {/* Status Card */}
                <View style={styles.card}>
                    <View style={styles.cardRow}>
                        <Text style={styles.cardLabel}>REQUEST ID</Text>
                        <Text style={styles.cardValue}>#{rideId}</Text>
                    </View>
                    <View style={[styles.cardDivider]} />
                    <View style={styles.cardRow}>
                        <Text style={styles.cardLabel}>VEHICLE</Text>
                        <Text style={styles.cardValue}>{vehicle.name}</Text>
                    </View>
                    <View style={styles.cardDivider} />
                    <View style={styles.cardRow}>
                        <Text style={styles.cardLabel}>STATUS</Text>
                        <View style={styles.statusChip}>
                            <Animated.View
                                style={[styles.statusDot, { backgroundColor: statusColor, opacity: dotAnim }]}
                            />
                            <Text style={[styles.statusText, { color: statusColor }]}>
                                {statusLabel}
                            </Text>
                        </View>
                    </View>
                </View>

                {/* Cancel */}
                <TouchableOpacity style={styles.cancelBtn} onPress={handleCancel} activeOpacity={0.8}>
                    <Text style={styles.cancelText}>Cancel Request</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}

const RING_SIZE = 180;

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#000",
    },

    // Radar
    radarZone: {
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
    },
    ring: {
        position: "absolute",
        width: RING_SIZE,
        height: RING_SIZE,
        borderRadius: RING_SIZE / 2,
        borderWidth: 1.5,
        borderColor: "#276EF1",
    },
    vehicleCircle: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: "rgba(39,110,241,0.12)",
        borderWidth: 1.5,
        borderColor: "rgba(39,110,241,0.4)",
        alignItems: "center",
        justifyContent: "center",
    },
    vehicleEmoji: { fontSize: 38 },

    // Info
    infoZone: {
        paddingHorizontal: 24,
        paddingBottom: 48,
    },
    title: {
        fontSize: 34,
        fontWeight: "900",
        color: "#FFFFFF",
        letterSpacing: -1,
        lineHeight: 40,
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 14,
        color: "#555",
        fontWeight: "500",
        marginBottom: 24,
    },

    // Card
    card: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        padding: 20,
        marginBottom: 16,
    },
    cardRow: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        paddingVertical: 6,
    },
    cardLabel: {
        fontSize: 11,
        fontWeight: "700",
        color: "#444",
        letterSpacing: 1,
    },
    cardValue: {
        fontSize: 13,
        fontWeight: "800",
        color: "#FFFFFF",
    },
    cardDivider: {
        height: 1,
        backgroundColor: "rgba(255,255,255,0.05)",
        marginVertical: 4,
    },
    statusChip: {
        flexDirection: "row",
        alignItems: "center",
        gap: 6,
    },
    statusDot: {
        width: 7,
        height: 7,
        borderRadius: 4,
    },
    statusText: {
        fontSize: 13,
        fontWeight: "800",
    },

    // Cancel
    cancelBtn: {
        backgroundColor: "rgba(255,255,255,0.06)",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
        paddingVertical: 18,
        borderRadius: 14,
        alignItems: "center",
    },
    cancelText: {
        color: "#fff",
        fontWeight: "700",
        fontSize: 16,
    },
});
