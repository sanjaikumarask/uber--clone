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
        try { if (rideId) await api.post(`rides/${rideId}/reject/`); } catch (_) { }
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
            await api.post(`rides/${rideId}/accept/`);
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
        backgroundColor: "#020408",
        justifyContent: "center",
        padding: 20,
    },

    badge: {
        alignSelf: "center",
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 30,
        marginBottom: 16,
        borderWidth: 1,
    },
    badgeOffer: { backgroundColor: "rgba(39,110,241,0.1)", borderColor: "rgba(39,110,241,0.3)" },
    badgeAuto: { backgroundColor: "rgba(239,68,68,0.1)", borderColor: "rgba(239,68,68,0.3)" },
    badgeText: { color: "#f8fafc", fontWeight: "800", fontSize: 11, letterSpacing: 1.5, textTransform: "uppercase" },

    warningBanner: {
        borderRadius: 16,
        paddingHorizontal: 16,
        paddingVertical: 12,
        marginBottom: 16,
        borderWidth: 1,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 10,
    },
    warningRed: { backgroundColor: "rgba(239,68,68,0.15)", borderColor: "rgba(239,68,68,0.4)" },
    warningOrange: { backgroundColor: "rgba(245,158,11,0.15)", borderColor: "rgba(245,158,11,0.4)" },
    warningText: { color: "#fff", fontSize: 13, fontWeight: "700", textAlign: "center", letterSpacing: 0.3 },

    card: {
        backgroundColor: "rgba(15,23,42,0.8)",
        padding: 28,
        borderRadius: 32,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 20 },
        shadowOpacity: 0.5,
        shadowRadius: 40,
        elevation: 10,
    },

    riderBox: {
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: "rgba(255,255,255,0.03)",
        padding: 16,
        borderRadius: 20,
        marginBottom: 24,
        gap: 16,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.05)",
    },
    avatar: {
        width: 56, height: 56, borderRadius: 18,
        backgroundColor: "#276EF1",
        justifyContent: "center", alignItems: "center",
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.4,
        shadowRadius: 12,
    },
    avatarTxt: { color: "#fff", fontWeight: "900", fontSize: 24 },
    riderName: { fontSize: 18, fontWeight: "800", color: "#f8fafc", letterSpacing: -0.5 },
    riderRating: { fontSize: 14, color: "#94a3b8", marginTop: 4, fontWeight: "600" },
    fareBadge: {
        alignItems: "center",
        backgroundColor: "rgba(34,197,94,0.1)",
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: "rgba(34,197,94,0.3)",
    },
    fareAmount: { fontSize: 24, fontWeight: "900", color: "#22C55E", letterSpacing: -1 },
    fareLabel: { fontSize: 9, color: "#22C55E", fontWeight: "900", textTransform: "uppercase", letterSpacing: 1, marginTop: 2, opacity: 0.8 },

    routeBox: {
        backgroundColor: "rgba(255,255,255,0.02)",
        borderRadius: 24,
        padding: 20,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.04)",
    },
    locationRow: { flexDirection: "row", alignItems: "flex-start", gap: 16 },
    dot: { width: 12, height: 12, borderRadius: 6, marginTop: 6, flexShrink: 0, borderWidth: 2, borderColor: "rgba(0,0,0,0.5)" },
    connector: { width: 2, height: 28, backgroundColor: "rgba(255,255,255,0.08)", marginLeft: 5, marginVertical: 4, borderRadius: 1 },
    locLabel: { fontSize: 9, color: "#64748b", fontWeight: "900", letterSpacing: 1.5, marginBottom: 6, textTransform: "uppercase" },
    locText: { fontSize: 15, color: "#cbd5e1", fontWeight: "600", lineHeight: 20 },

    rideId: { color: "rgba(255,255,255,0.2)", fontSize: 10, textAlign: "right", marginBottom: 20, fontWeight: "700", letterSpacing: 1 },

    timerRow: {
        flexDirection: "row",
        alignItems: "center",
        gap: 20,
        marginBottom: 20,
    },
    timerRing: {
        width: 90, height: 90, borderRadius: 45,
        borderWidth: 4,
        justifyContent: "center", alignItems: "center",
        backgroundColor: "rgba(0,0,0,0.3)",
        flexShrink: 0,
    },
    timerNum: { fontSize: 36, fontWeight: "900", lineHeight: 40, letterSpacing: -1 },
    timerSec: { fontSize: 10, fontWeight: "900", textTransform: "uppercase", letterSpacing: 1, marginTop: -4 },
    timerInfo: { flex: 1 },
    timerTitle: { color: "#fff", fontSize: 18, fontWeight: "800", marginBottom: 6, letterSpacing: -0.5 },
    timerSub: { color: "#64748b", fontSize: 13, lineHeight: 18, fontWeight: "500" },

    progressTrack: {
        height: 6, backgroundColor: "rgba(255,255,255,0.05)",
        borderRadius: 3, overflow: "hidden",
        marginBottom: 28,
    },
    progressBar: { height: "100%", borderRadius: 3 },

    goBtn: {
        backgroundColor: "#FF6B00",
        padding: 20, borderRadius: 20,
        alignItems: "center",
        shadowColor: "#FF6B00",
        shadowOffset: { width: 0, height: 12 },
        shadowOpacity: 0.4,
        shadowRadius: 20,
    },
    goBtnText: { color: "#fff", fontSize: 18, fontWeight: "900", letterSpacing: 0.5 },

    btnRow: { flexDirection: "row", gap: 16 },
    rejectBtn: {
        flex: 1, padding: 20, borderRadius: 20,
        borderWidth: 1.5, borderColor: "rgba(239,68,68,0.4)",
        backgroundColor: "rgba(239,68,68,0.05)",
        alignItems: "center",
    },
    rejectTxt: { color: "#EF4444", fontSize: 15, fontWeight: "800", textTransform: "uppercase", letterSpacing: 1 },
    acceptBtn: {
        flex: 1, padding: 20, borderRadius: 20,
        borderWidth: 1.5, borderColor: "rgba(34,197,94,0.4)",
        backgroundColor: "rgba(34,197,94,0.05)",
        alignItems: "center",
        shadowColor: "#22C55E",
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.2,
        shadowRadius: 15,
    },
    acceptTxt: { color: "#22C55E", fontSize: 15, fontWeight: "800", textTransform: "uppercase", letterSpacing: 1 },
});
