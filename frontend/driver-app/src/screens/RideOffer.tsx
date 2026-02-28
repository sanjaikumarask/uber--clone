import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Animated, Alert } from "react-native";
import { api } from "../services/api";

const AUTO_ASSIGN_THRESHOLD = 3; // matches backend

export default function RideOfferScreen({ route, navigation }: any) {
    const { offer } = route.params || {};

    console.log("[RideOffer] payload v5:", JSON.stringify(offer, null, 2));

    const rideId = offer?.ride_id;
    const pickup = offer?.pickup;
    const drop = offer?.drop;
    const fare = offer?.fare_estimate;
    const isAutoAssigned = !!offer?.is_auto_assigned;
    const rejectionCount = offer?.rejection_count ?? 0;        // how many today
    const leftUntilAuto = offer?.rejections_until_auto ?? 0;  // how many left before auto
    const offerTimeout = offer?.timeout ?? 60;               // from backend (60s)

    // ── Countdown ─────────────────────────────────────────────────
    const [secondsLeft, setSecondsLeft] = useState(isAutoAssigned ? 5 : offerTimeout);
    const timerRef = useRef<any>(null);

    // Animated progress bar (normal offer only)
    const progress = useRef(new Animated.Value(1)).current;

    useEffect(() => {
        if (!isAutoAssigned) {
            Animated.timing(progress, {
                toValue: 0,
                duration: offerTimeout * 1000,
                useNativeDriver: false,
            }).start();
        }

        timerRef.current = setInterval(() => {
            setSecondsLeft((prev: number) => {
                const next = prev - 1;
                return next < 0 ? 0 : next;
            });
        }, 1000) as any;

        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, []);

    // Observer to handle timeouts gracefully without breaking React's render purity
    useEffect(() => {
        if (secondsLeft <= 0) {
            if (timerRef.current) clearInterval(timerRef.current);
            // Escape React's synchronous render loop to prevent BaseNavigationContainer conflict
            setTimeout(() => {
                if (isAutoAssigned) {
                    navigation.replace("RideTracking", { rideId });
                } else {
                    silentReject();
                    navigation.goBack();
                }
            }, 0);
        }
    }, [secondsLeft]);

    async function silentReject() {
        try { if (rideId) await api.post(`/rides/${rideId}/reject/`); } catch (_) { }
    }

    // ── Location display ──────────────────────────────────────────
    const pickupText = offer?.pickup_address
        ? offer.pickup_address
        : (typeof pickup === "object" && pickup?.lat)
            ? `${Number(pickup.lat).toFixed(5)}, ${Number(pickup.lng).toFixed(5)}`
            : "Unknown pickup";

    const dropText = offer?.drop_address
        ? offer.drop_address
        : (typeof drop === "object" && drop?.lat)
            ? `${Number(drop.lat).toFixed(5)}, ${Number(drop.lng).toFixed(5)}`
            : "Unknown dropoff";

    // ── Handlers ──────────────────────────────────────────────────
    async function handleAccept() {
        if (timerRef.current) clearInterval(timerRef.current);
        try {
            await api.post(`/rides/${rideId}/accept/`);
            navigation.replace("RideTracking", { rideId });
        } catch (err: any) {
            const msg = err?.response?.data?.error || "Failed to accept ride";
            Alert.alert("Action Failed", msg);
        }
    }

    async function handleReject() {
        if (timerRef.current) clearInterval(timerRef.current);
        await silentReject();
        navigation.goBack();
    }

    // ── Dynamic colour for countdown ring ────────────────────────
    const ringColor = isAutoAssigned
        ? "#FF6B00"
        : secondsLeft <= 10 ? "#FF3B30"
            : secondsLeft <= 25 ? "#FF9500"
                : "#276EF1";

    // ── Rejection warning label ───────────────────────────────────
    const rejectionWarning = !isAutoAssigned && rejectionCount > 0
        ? leftUntilAuto === 1
            ? `⚠️  1 more rejection → Auto-assigned!`
            : `ℹ️  ${rejectionCount} rejection${rejectionCount > 1 ? "s" : ""} today — ${leftUntilAuto} left before auto-assign`
        : null;

    // ─────────────────────────────────────────────────────────────
    return (
        <View style={styles.container}>

            {/* Top badge */}
            <View style={[styles.badge, isAutoAssigned ? styles.badgeAuto : styles.badgeOffer]}>
                <Text style={styles.badgeText}>
                    {isAutoAssigned ? "⚡ Auto-Assigned — No Reject Option" : "🚖 New Ride Request"}
                </Text>
            </View>

            {/* Rejection warning (normal offer only) */}
            {rejectionWarning && (
                <View style={[
                    styles.warningBanner,
                    leftUntilAuto === 1 ? styles.warningRed : styles.warningOrange
                ]}>
                    <Text style={styles.warningText}>{rejectionWarning}</Text>
                </View>
            )}

            <View style={styles.card}>

                {/* Rider + Fare row */}
                <View style={styles.riderBox}>
                    <View style={styles.avatar}>
                        <Text style={styles.avatarTxt}>
                            {offer?.rider?.name?.[0]?.toUpperCase() || "R"}
                        </Text>
                    </View>
                    <View style={{ flex: 1 }}>
                        <Text style={styles.riderName}>{offer?.rider?.name || "Rider"}</Text>
                        <Text style={styles.riderRating}>
                            ⭐ {Number(offer?.rider?.rating || 5.0).toFixed(1)}
                        </Text>
                    </View>
                    <View style={styles.fareBadge}>
                        <Text style={styles.fareAmount}>
                            ₹{fare ? Number(fare).toFixed(0) : "—"}
                        </Text>
                        <Text style={styles.fareLabel}>est. fare</Text>
                    </View>
                </View>

                {/* Route */}
                <View style={styles.routeBox}>
                    <View style={styles.locationRow}>
                        <View style={[styles.dot, { backgroundColor: "#34C759" }]} />
                        <View style={{ flex: 1 }}>
                            <Text style={styles.locLabel}>PICKUP</Text>
                            <Text style={styles.locText} numberOfLines={2}>{pickupText}</Text>
                        </View>
                    </View>
                    <View style={styles.connector} />
                    <View style={styles.locationRow}>
                        <View style={[styles.dot, { backgroundColor: "#FF3B30" }]} />
                        <View style={{ flex: 1 }}>
                            <Text style={styles.locLabel}>DROP-OFF</Text>
                            <Text style={styles.locText} numberOfLines={2}>{dropText}</Text>
                        </View>
                    </View>
                </View>

                <Text style={styles.rideId}>Ride #{rideId || "—"}</Text>

                {/* Countdown ring */}
                <View style={styles.timerRow}>
                    <View style={[styles.timerRing, { borderColor: ringColor }]}>
                        <Text style={[styles.timerNum, { color: ringColor }]}>{secondsLeft}</Text>
                        <Text style={[styles.timerSec, { color: ringColor }]}>sec</Text>
                    </View>
                    <View style={styles.timerInfo}>
                        {isAutoAssigned ? (
                            <>
                                <Text style={styles.timerTitle}>Auto-assigned</Text>
                                <Text style={styles.timerSub}>
                                    You exceeded {AUTO_ASSIGN_THRESHOLD} rejections today.{"\n"}
                                    This ride cannot be rejected.
                                </Text>
                            </>
                        ) : (
                            <>
                                <Text style={styles.timerTitle}>
                                    {secondsLeft <= 10 ? "⚠️ Hurry!" : "Respond now"}
                                </Text>
                                <Text style={styles.timerSub}>
                                    Auto-rejects when timer hits 0
                                </Text>
                            </>
                        )}
                    </View>
                </View>

                {/* Progress bar — normal offer only */}
                {!isAutoAssigned && (
                    <View style={styles.progressTrack}>
                        <Animated.View style={[
                            styles.progressBar,
                            {
                                backgroundColor: ringColor,
                                width: progress.interpolate({
                                    inputRange: [0, 1],
                                    outputRange: ["0%", "100%"],
                                }),
                            }
                        ]} />
                    </View>
                )}

                {/* Action buttons */}
                {isAutoAssigned ? (
                    <TouchableOpacity
                        style={styles.goBtn}
                        onPress={() => {
                            if (timerRef.current) clearInterval(timerRef.current);
                            navigation.replace("RideTracking", { rideId });
                        }}
                    >
                        <Text style={styles.goBtnText}>Start Ride Now →</Text>
                    </TouchableOpacity>
                ) : (
                    <View style={styles.btnRow}>
                        <TouchableOpacity style={styles.rejectBtn} onPress={handleReject}>
                            <Text style={styles.rejectTxt}>✕  Reject</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.acceptBtn} onPress={handleAccept}>
                            <Text style={styles.acceptTxt}>✓  Accept</Text>
                        </TouchableOpacity>
                    </View>
                )}
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#0d0d0d",
        justifyContent: "center",
        padding: 18,
    },

    badge: {
        alignSelf: "center",
        paddingHorizontal: 16,
        paddingVertical: 7,
        borderRadius: 20,
        marginBottom: 10,
    },
    badgeOffer: { backgroundColor: "#1A3A5C" },
    badgeAuto: { backgroundColor: "#5C1A1A" },
    badgeText: { color: "#fff", fontWeight: "700", fontSize: 13, letterSpacing: 0.3 },

    // Rejection warning banner
    warningBanner: {
        borderRadius: 10,
        paddingHorizontal: 14,
        paddingVertical: 9,
        marginBottom: 10,
        borderWidth: 1,
    },
    warningRed: { backgroundColor: "#2a0808", borderColor: "#FF3B30" },
    warningOrange: { backgroundColor: "#2a1800", borderColor: "#FF9500" },
    warningText: { color: "#fff", fontSize: 12, fontWeight: "600", textAlign: "center" },

    card: {
        backgroundColor: "#1a1a1a",
        padding: 22,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "#2a2a2a",
    },

    // Rider row
    riderBox: {
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: "#111",
        padding: 13,
        borderRadius: 14,
        marginBottom: 14,
        gap: 12,
    },
    avatar: {
        width: 48, height: 48, borderRadius: 24,
        backgroundColor: "#276EF1",
        justifyContent: "center", alignItems: "center",
    },
    avatarTxt: { color: "#fff", fontWeight: "bold", fontSize: 20 },
    riderName: { fontSize: 15, fontWeight: "700", color: "#fff" },
    riderRating: { fontSize: 13, color: "#aaa", marginTop: 2 },
    fareBadge: {
        alignItems: "center",
        backgroundColor: "#0a230a",
        paddingHorizontal: 13,
        paddingVertical: 8,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: "#1e5c1e",
    },
    fareAmount: { fontSize: 22, fontWeight: "800", color: "#34C759" },
    fareLabel: { fontSize: 10, color: "#34C759", opacity: 0.75 },

    // Route
    routeBox: {
        backgroundColor: "#111",
        borderRadius: 14,
        padding: 14,
        marginBottom: 10,
    },
    locationRow: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
    dot: { width: 11, height: 11, borderRadius: 6, marginTop: 4, flexShrink: 0 },
    connector: { width: 2, height: 20, backgroundColor: "#2a2a2a", marginLeft: 4, marginVertical: 3 },
    locLabel: { fontSize: 10, color: "#555", fontWeight: "700", letterSpacing: 0.8, marginBottom: 1 },
    locText: { fontSize: 14, color: "#ddd", fontWeight: "500" },

    rideId: { color: "#444", fontSize: 11, textAlign: "right", marginBottom: 14 },

    // Timer
    timerRow: {
        flexDirection: "row",
        alignItems: "center",
        gap: 16,
        marginBottom: 12,
    },
    timerRing: {
        width: 80, height: 80, borderRadius: 40,
        borderWidth: 3,
        justifyContent: "center", alignItems: "center",
        backgroundColor: "#111",
        flexShrink: 0,
    },
    timerNum: { fontSize: 30, fontWeight: "800", lineHeight: 34 },
    timerSec: { fontSize: 10, fontWeight: "600" },
    timerInfo: { flex: 1 },
    timerTitle: { color: "#fff", fontSize: 15, fontWeight: "700", marginBottom: 4 },
    timerSub: { color: "#777", fontSize: 12, lineHeight: 17 },

    // Progress bar
    progressTrack: {
        height: 4, backgroundColor: "#222",
        borderRadius: 2, overflow: "hidden",
        marginBottom: 16,
    },
    progressBar: { height: "100%", borderRadius: 2 },

    // Auto-assigned CTA
    goBtn: {
        backgroundColor: "#FF6B00",
        padding: 16, borderRadius: 14,
        alignItems: "center",
    },
    goBtnText: { color: "#fff", fontSize: 16, fontWeight: "700", letterSpacing: 0.3 },

    // Normal offer buttons
    btnRow: { flexDirection: "row", gap: 12 },
    rejectBtn: {
        flex: 1, padding: 16, borderRadius: 14,
        borderWidth: 1.5, borderColor: "#FF3B30",
        backgroundColor: "#150404",
        alignItems: "center",
    },
    rejectTxt: { color: "#FF3B30", fontSize: 15, fontWeight: "700" },
    acceptBtn: {
        flex: 1, padding: 16, borderRadius: 14,
        borderWidth: 1.5, borderColor: "#34C759",
        backgroundColor: "#041504",
        alignItems: "center",
    },
    acceptTxt: { color: "#34C759", fontSize: 15, fontWeight: "700" },
});
