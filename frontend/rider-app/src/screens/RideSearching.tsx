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
                const res = await api.get(`rides/${rideId}/`);
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
            await api.post(`rides/${rideId}/cancel/`);
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
        backgroundColor: "#020408",
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
        borderColor: "rgba(39,110,241,0.4)",
    },
    vehicleCircle: {
        width: 100,
        height: 100,
        borderRadius: 32,
        backgroundColor: "rgba(15,23,42,0.8)",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
        alignItems: "center",
        justifyContent: "center",
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 12 },
        shadowOpacity: 0.3,
        shadowRadius: 24,
        elevation: 10,
    },
    vehicleEmoji: { fontSize: 48 },

    // Info
    infoZone: {
        paddingHorizontal: 28,
        paddingBottom: 64,
    },
    title: {
        fontSize: 38,
        fontWeight: "900",
        color: "#f8fafc",
        letterSpacing: -1.5,
        lineHeight: 44,
        marginBottom: 12,
    },
    subtitle: {
        fontSize: 16,
        color: "#64748b",
        fontWeight: "600",
        marginBottom: 32,
    },

    // Card
    card: {
        backgroundColor: "rgba(15,23,42,0.4)",
        borderRadius: 28,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        padding: 24,
        marginBottom: 24,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 20 },
        shadowOpacity: 0.3,
        shadowRadius: 40,
    },
    cardRow: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        paddingVertical: 10,
    },
    cardLabel: {
        fontSize: 10,
        fontWeight: "900",
        color: "#64748b",
        letterSpacing: 1.5,
        textTransform: "uppercase"
    },
    cardValue: {
        fontSize: 14,
        fontWeight: "800",
        color: "#f1f5f9",
    },
    cardDivider: {
        height: 1,
        backgroundColor: "rgba(255,255,255,0.06)",
        marginVertical: 4,
    },
    statusChip: {
        flexDirection: "row",
        alignItems: "center",
        gap: 10,
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    statusText: {
        fontSize: 14,
        fontWeight: "900",
        textTransform: "uppercase",
        letterSpacing: 0.5,
    },

    // Cancel
    cancelBtn: {
        backgroundColor: "rgba(255,255,255,0.03)",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.07)",
        paddingVertical: 20,
        borderRadius: 20,
        alignItems: "center",
    },
    cancelText: {
        color: "#64748b",
        fontWeight: "800",
        fontSize: 14,
        textTransform: "uppercase",
        letterSpacing: 1,
    },
});
