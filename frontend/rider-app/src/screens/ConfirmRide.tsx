import React, { useState } from "react";
import {
    View, Text, StyleSheet, TouchableOpacity, ActivityIndicator,
    Alert, Dimensions, ScrollView, StatusBar, Platform
} from "react-native";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import { api } from "../services/api";

const { width } = Dimensions.get("window");

// ── Dark Map Style (Midnight Grey) ─────────────────────────────────────────────
const mapStyle = [
    { "elementType": "geometry", "stylers": [{ "color": "#1A1B1F" }] },
    { "elementType": "labels.icon", "stylers": [{ "visibility": "off" }] },
    { "elementType": "labels.text.fill", "stylers": [{ "color": "#777777" }] },
    { "elementType": "labels.text.stroke", "stylers": [{ "color": "#1A1B1F" }] },
    { "featureType": "administrative.locality", "elementType": "labels.text.fill", "stylers": [{ "color": "#999999" }] },
    { "featureType": "poi", "stylers": [{ "visibility": "off" }] },
    { "featureType": "road", "elementType": "geometry.fill", "stylers": [{ "color": "#2A2D32" }] },
    { "featureType": "road", "elementType": "labels.text.fill", "stylers": [{ "color": "#555555" }] },
    { "featureType": "road.arterial", "elementType": "geometry", "stylers": [{ "color": "#33373E" }] },
    { "featureType": "road.highway", "elementType": "geometry", "stylers": [{ "color": "#3D4148" }] },
    { "featureType": "water", "elementType": "geometry", "stylers": [{ "color": "#0D1117" }] },
    { "featureType": "water", "elementType": "labels.text.fill", "stylers": [{ "color": "#1a1a1a" }] }
];

// ── Vehicle Types ──────────────────────────────────────────────────────────────
const VEHICLE_TYPES = [
    {
        id: "moto",
        name: "Uber Moto",
        emoji: "🏍️",
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
        emoji: "🛺",
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
        emoji: "🚗",
        multiplier: 1.0,
        desc: "Affordable, compact",
        tag: null,
        tagColor: "transparent",
        accent: "#276EF1",
        seats: 4,
    },
    {
        id: "xl",
        name: "UberXL",
        emoji: "🚙",
        multiplier: 1.4,
        desc: "Comfortable SUVs",
        tag: null,
        tagColor: "transparent",
        accent: "#8b5cf6",
        seats: 6,
    },
];

export default function ConfirmRideScreen({ navigation, route }: any) {
    const { destination, pickupLocation } = route.params;
    const [loading, setLoading] = useState(false);
    const [fareLoading, setFareLoading] = useState(true);
    const [estimate, setEstimate] = useState<any>(null);
    const [selectedVehicle, setSelectedVehicle] = useState(VEHICLE_TYPES[2]); // default UberGo

    React.useEffect(() => {
        fetchEstimate();
    }, []);

    const fetchEstimate = async () => {
        try {
            const res = await api.post("/rides/estimate-fare/", {
                pickup_lat: pickupLocation.lat,
                pickup_lng: pickupLocation.lng,
                drop_lat: destination.lat,
                drop_lng: destination.lng,
            });
            setEstimate(res.data);
        } catch (err) {
            console.error("Fare estimation failed", err);
        } finally {
            setFareLoading(false);
        }
    };

    const handleConfirmRide = async () => {
        setLoading(true);
        try {
            const res = await api.post("/rides/request/", {
                pickup_lat: pickupLocation.lat,
                pickup_lng: pickupLocation.lng,
                pickup_address: pickupLocation.address || "My Location",
                drop_lat: destination.lat,
                drop_lng: destination.lng,
                drop_address: destination.description,
                vehicle_type: selectedVehicle.id,
            });

            navigation.replace("RideSearching", {
                rideId: res.data.id,
                vehicleType: selectedVehicle.id,
            });
        } catch (err: any) {
            if (err.response?.status === 409) {
                Alert.alert("Active Ride Found", "Redirecting to your current ride...");
                try {
                    const activeRes = await api.get("/rides/active/");
                    if (activeRes.data.id) {
                        navigation.replace("RideTracking", { rideId: activeRes.data.id });
                        return;
                    }
                } catch (e) { }
            } else {
                Alert.alert("Error", err.response?.data?.error || "Failed to request ride.");
            }
        } finally {
            setLoading(false);
        }
    };

    const getFare = (vt: typeof VEHICLE_TYPES[0]) =>
        estimate ? `₹${Math.round(estimate.estimated_fare * vt.multiplier)}` : "—";

    return (
        <View style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor="#000" />

            {/* ── Map ── */}
            <View style={styles.mapContainer}>
                <MapView
                    provider={PROVIDER_GOOGLE}
                    style={styles.map}
                    customMapStyle={mapStyle}
                    initialRegion={{
                        latitude: (pickupLocation.lat + destination.lat) / 2,
                        longitude: (pickupLocation.lng + destination.lng) / 2,
                        latitudeDelta: Math.abs(pickupLocation.lat - destination.lat) * 2.5 + 0.02,
                        longitudeDelta: Math.abs(pickupLocation.lng - destination.lng) * 2.5 + 0.02,
                    }}
                >
                    {/* Pickup */}
                    <Marker coordinate={{ latitude: pickupLocation.lat, longitude: pickupLocation.lng }} title="Pickup">
                        <View style={styles.pickupDot} />
                    </Marker>
                    {/* Drop */}
                    <Marker coordinate={{ latitude: destination.lat, longitude: destination.lng }} title="Drop">
                        <View style={styles.dropDot} />
                    </Marker>
                </MapView>
            </View>

            {/* ── Bottom Overlay Panel ── */}
            <View style={styles.panel}>
                {/* Header */}
                <View style={styles.panelHeader}>
                    <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
                        <Text style={styles.backArrow}>←</Text>
                    </TouchableOpacity>
                    <View style={{ flex: 1 }}>
                        <Text style={styles.panelTitle}>Choose a ride</Text>
                        {estimate && !fareLoading && (
                            <Text style={styles.routeInfo}>
                                {Number(estimate.distance_km).toFixed(1)} km · {Math.ceil(estimate.duration_min)} min
                                {estimate.surge_multiplier > 1 && "  🔥 High Demand"}
                            </Text>
                        )}
                    </View>
                </View>

                {/* Route preview */}
                <View style={styles.routeRow}>
                    <View style={styles.routeDots}>
                        <View style={styles.dotWhite} />
                        <View style={styles.routeLine} />
                        <View style={styles.dotBlue} />
                    </View>
                    <View style={styles.routeAddresses}>
                        <Text style={styles.routeText} numberOfLines={1}>
                            {pickupLocation.address || "My Location"}
                        </Text>
                        <Text style={styles.routeText} numberOfLines={1}>
                            {destination.description}
                        </Text>
                    </View>
                </View>

                {/* Vehicle List */}
                <ScrollView style={styles.vehicleList} showsVerticalScrollIndicator={false}>
                    {VEHICLE_TYPES.map((vt) => {
                        const selected = selectedVehicle.id === vt.id;
                        return (
                            <TouchableOpacity
                                key={vt.id}
                                onPress={() => setSelectedVehicle(vt)}
                                style={[styles.vehicleCard, selected && { borderColor: vt.accent, backgroundColor: `${vt.accent}18` }]}
                                activeOpacity={0.8}
                            >
                                {/* Emoji icon */}
                                <Text style={styles.vehicleEmoji}>{vt.emoji}</Text>

                                {/* Name + desc */}
                                <View style={styles.vehicleInfo}>
                                    <View style={styles.vehicleNameRow}>
                                        <Text style={styles.vehicleName}>{vt.name}</Text>
                                        {vt.tag && (
                                            <View style={[styles.tag, { backgroundColor: `${vt.tagColor}22` }]}>
                                                <Text style={[styles.tagText, { color: vt.tagColor }]}>{vt.tag}</Text>
                                            </View>
                                        )}
                                    </View>
                                    <Text style={styles.vehicleDesc}>{vt.desc}</Text>
                                </View>

                                {/* Fare */}
                                <View style={styles.fareCol}>
                                    <Text style={[styles.farePrice, selected && { color: vt.accent }]}>
                                        {fareLoading ? "…" : getFare(vt)}
                                    </Text>
                                    <Text style={styles.seatsText}>👥 {vt.seats}</Text>
                                </View>

                                {/* Selected check */}
                                {selected && (
                                    <View style={[styles.checkCircle, { backgroundColor: vt.accent }]}>
                                        <Text style={styles.checkMark}>✓</Text>
                                    </View>
                                )}
                            </TouchableOpacity>
                        );
                    })}
                </ScrollView>

                {/* Confirm Button */}
                <TouchableOpacity
                    style={[styles.confirmBtn, { backgroundColor: selectedVehicle.accent }, loading && styles.btnDisabled]}
                    onPress={handleConfirmRide}
                    disabled={loading || fareLoading}
                    activeOpacity={0.85}
                >
                    {loading ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <Text style={styles.confirmText}>
                            Confirm {selectedVehicle.name}
                        </Text>
                    )}
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: "#000" },

    // Map
    mapContainer: { flex: 1 },
    map: { flex: 1 },
    pickupDot: { width: 14, height: 14, borderRadius: 7, backgroundColor: "#FFFFFF", borderWidth: 3, borderColor: "#000" },
    dropDot: { width: 14, height: 14, borderRadius: 3, backgroundColor: "#276EF1", borderWidth: 3, borderColor: "#000" },

    // Panel
    panel: {
        position: "absolute",
        bottom: 0, left: 0, right: 0,
        backgroundColor: "rgba(10,10,10,0.97)",
        borderTopLeftRadius: 28,
        borderTopRightRadius: 28,
        borderTopWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        paddingHorizontal: 20,
        paddingTop: 20,
        paddingBottom: Platform.OS === "ios" ? 36 : 24,
        maxHeight: "72%",
    },
    panelHeader: {
        flexDirection: "row",
        alignItems: "flex-start",
        marginBottom: 16,
        gap: 12,
    },
    backBtn: {
        width: 36, height: 36, borderRadius: 18,
        backgroundColor: "rgba(255,255,255,0.08)",
        borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
        alignItems: "center", justifyContent: "center",
    },
    backArrow: { fontSize: 16, color: "#fff", fontWeight: "700" },
    panelTitle: { fontSize: 18, fontWeight: "900", color: "#FFFFFF", marginBottom: 2 },
    routeInfo: { fontSize: 12, color: "#666", fontWeight: "600" },

    // Route Preview
    routeRow: {
        flexDirection: "row",
        alignItems: "center",
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 14,
        padding: 14,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.07)",
        gap: 12,
    },
    routeDots: { alignItems: "center", gap: 2 },
    dotWhite: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#fff" },
    routeLine: { width: 1, height: 16, backgroundColor: "rgba(255,255,255,0.2)" },
    dotBlue: { width: 8, height: 8, borderRadius: 2, backgroundColor: "#276EF1" },
    routeAddresses: { flex: 1, gap: 6 },
    routeText: { fontSize: 13, color: "#A6A6A6", fontWeight: "500" },

    // Vehicle Cards
    vehicleList: { maxHeight: 260 },
    vehicleCard: {
        flexDirection: "row",
        alignItems: "center",
        padding: 16,
        borderRadius: 16,
        borderWidth: 1.5,
        borderColor: "rgba(255,255,255,0.1)",
        backgroundColor: "rgba(255,255,255,0.04)",
        marginBottom: 10,
        position: "relative",
    },
    vehicleEmoji: { fontSize: 36, marginRight: 14, width: 50, textAlign: "center" },
    vehicleInfo: { flex: 1 },
    vehicleNameRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 3 },
    vehicleName: { fontSize: 15, fontWeight: "800", color: "#fff" },
    tag: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
    tagText: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
    vehicleDesc: { fontSize: 12, color: "#666" },
    fareCol: { alignItems: "flex-end" },
    farePrice: { fontSize: 18, fontWeight: "900", color: "#fff" },
    seatsText: { fontSize: 11, color: "#555", marginTop: 2 },
    checkCircle: {
        position: "absolute", top: 10, right: 10,
        width: 20, height: 20, borderRadius: 10,
        alignItems: "center", justifyContent: "center",
    },
    checkMark: { color: "#fff", fontSize: 11, fontWeight: "900" },

    // Confirm Button
    confirmBtn: {
        borderRadius: 16,
        paddingVertical: 16,
        alignItems: "center",
        justifyContent: "center",
        marginTop: 10,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 6,
    },
    btnDisabled: { opacity: 0.65 },
    confirmText: {
        color: "#fff",
        fontSize: 18,
        fontWeight: "800",
    },
});
