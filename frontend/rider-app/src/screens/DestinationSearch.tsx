import React, { useState, useEffect, useRef } from "react";
import { StyleSheet, View, TouchableOpacity, Text, StatusBar, ActivityIndicator, Dimensions } from "react-native";
import { GooglePlacesAutocomplete } from "react-native-google-places-autocomplete";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import { api } from "../services/api";
import { GOOGLE_MAPS_APIKEY } from "../config";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Location from "expo-location";

const { width, height } = Dimensions.get("window");

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

export default function DestinationSearchScreen({ navigation }: any) {
    const pickupRef = useRef<any>(null);
    const mapRef = useRef<MapView>(null);
    const [pickup, setPickup] = useState<any>({
        lat: 13.0827,
        lng: 80.2707,
        address: "Current Location",
    });
    const [fetchingLocation, setFetchingLocation] = useState(true);
    const [nearbyDrivers, setNearbyDrivers] = useState<any[]>([]);

    useEffect(() => {
        if (pickup.lat && mapRef.current) {
            mapRef.current.animateToRegion({
                latitude: pickup.lat,
                longitude: pickup.lng,
                latitudeDelta: 0.015,
                longitudeDelta: 0.015,
            }, 1000);
        }
    }, [pickup.lat, pickup.lng]);

    useEffect(() => {
        (async () => {
            let { status } = await Location.requestForegroundPermissionsAsync();
            if (status !== "granted") {
                setFetchingLocation(false);
                pickupRef.current?.setAddressText("Chennai, TN");
                return;
            }

            try {
                let location = await Location.getCurrentPositionAsync({});
                const res = await fetch(
                    `https://maps.googleapis.com/maps/api/geocode/json?latlng=${location.coords.latitude},${location.coords.longitude}&key=${GOOGLE_MAPS_APIKEY}`
                );
                const data = await res.json();
                if (data.results && data.results.length > 0) {
                    const addr = data.results[0].formatted_address;
                    const loc = { lat: location.coords.latitude, lng: location.coords.longitude, address: addr };
                    setPickup(loc);
                    pickupRef.current?.setAddressText(addr);
                    fetchNearbyDrivers(loc.lat, loc.lng);
                }
            } catch (e) {
                console.error("Location error", e);
            } finally {
                setFetchingLocation(false);
            }
        })();
    }, []);

    const fetchNearbyDrivers = async (lat: number, lng: number) => {
        try {
            const res = await api.post("/rides/nearby-drivers/", { lat, lng, radius_km: 5 });
            if (res.data?.drivers) {
                setNearbyDrivers(res.data.drivers);
            }
        } catch (err) {
            console.error("Failed to fetch nearby drivers", err);
        }
    };

    // Poll nearby drivers every 10 seconds
    useEffect(() => {
        if (!pickup.lat) return;
        const interval = setInterval(() => fetchNearbyDrivers(pickup.lat, pickup.lng), 10000);
        return () => clearInterval(interval);
    }, [pickup.lat, pickup.lng]);

    const handleSelectDestination = (data: any, details: any = null) => {
        if (!details) return;
        navigation.navigate("ConfirmRide", {
            destination: {
                lat: details.geometry.location.lat,
                lng: details.geometry.location.lng,
                description: data.description,
            },
            pickupLocation: pickup,
        });
    };

    return (
        <View style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />

            {/* Background Map */}
            <MapView
                ref={mapRef}
                provider={PROVIDER_GOOGLE}
                style={StyleSheet.absoluteFillObject}
                customMapStyle={mapStyle}
                initialRegion={{
                    latitude: pickup.lat,
                    longitude: pickup.lng,
                    latitudeDelta: 0.015,
                    longitudeDelta: 0.015,
                }}
            >
                {/* Pickup Marker */}
                <Marker
                    coordinate={{ latitude: pickup.lat, longitude: pickup.lng }}
                    anchor={{ x: 0.5, y: 0.5 }}
                >
                    <View style={styles.pickupMarker} />
                </Marker>

                {/* Nearby Driver Markers */}
                {nearbyDrivers.map((driver) => (
                    <Marker
                        key={driver.id}
                        coordinate={{ latitude: driver.lat, longitude: driver.lng }}
                        anchor={{ x: 0.5, y: 0.5 }}
                    >
                        <View style={styles.carMarker}>
                            <Text style={{ fontSize: 16 }}>🚕</Text>
                        </View>
                    </Marker>
                ))}
            </MapView>

            <SafeAreaView style={styles.overlay}>
                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn} activeOpacity={0.8}>
                        <Text style={styles.backArrow}>←</Text>
                    </TouchableOpacity>
                    <View>
                        <Text style={styles.headerTitle}>Plan your ride<Text style={styles.accent}>.</Text></Text>
                        <Text style={styles.headerSub}>Set your pickup and drop-off</Text>
                    </View>
                </View>

                <View style={styles.content}>
                    <View style={styles.searchPanel}>
                        {/* Pickup Section */}
                        <View style={styles.inputGroup}>
                            <View style={styles.dotLineContainer}>
                                <View style={styles.dotWhite} />
                                <View style={styles.line} />
                            </View>
                            <View style={styles.searchWrapper}>
                                <Text style={styles.inputLabel}>PICKUP</Text>
                                <GooglePlacesAutocomplete
                                    ref={pickupRef}
                                    placeholder="Search pickup location"
                                    nearbyPlacesAPI="GooglePlacesSearch"
                                    debounce={300}
                                    fetchDetails={true}
                                    enablePoweredByContainer={false}
                                    minLength={2}
                                    textInputProps={{
                                        placeholderTextColor: "#777",
                                        style: styles.textInput,
                                    }}
                                    renderRightButton={() =>
                                        fetchingLocation ? <ActivityIndicator size="small" color="#276EF1" style={{ marginRight: 15 }} /> : null
                                    }
                                    onPress={(data, details = null) => {
                                        if (details) {
                                            setPickup({
                                                lat: details.geometry.location.lat,
                                                lng: details.geometry.location.lng,
                                                address: data.description,
                                            });
                                        }
                                    }}
                                    query={{ key: GOOGLE_MAPS_APIKEY, language: "en", components: "country:in" }}
                                    styles={autoCompleteStyles}
                                />
                            </View>
                        </View>

                        {/* Destination Section */}
                        <View style={styles.inputGroup}>
                            <View style={[styles.dotLineContainer, { paddingTop: 26 }]}>
                                <View style={styles.dotBlue} />
                            </View>
                            <View style={styles.searchWrapper}>
                                <Text style={styles.inputLabel}>DESTINATION</Text>
                                <GooglePlacesAutocomplete
                                    placeholder="Where to?"
                                    nearbyPlacesAPI="GooglePlacesSearch"
                                    debounce={300}
                                    fetchDetails={true}
                                    enablePoweredByContainer={false}
                                    minLength={2}
                                    textInputProps={{
                                        placeholderTextColor: "#777",
                                        style: [styles.textInput, { borderColor: "#276EF1", backgroundColor: "rgba(39,110,241,0.08)" }],
                                        autoFocus: true,
                                    }}
                                    onPress={handleSelectDestination}
                                    query={{ key: GOOGLE_MAPS_APIKEY, language: "en", components: "country:in" }}
                                    styles={autoCompleteStyles}
                                />
                            </View>
                        </View>
                    </View>
                </View>
            </SafeAreaView>
        </View>
    );
}

const autoCompleteStyles = {
    container: { flex: 0 },
    listView: {
        backgroundColor: "#111111",
        marginTop: 4,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.07)",
        overflow: "hidden",
        zIndex: 1000,
        elevation: 1000,
    },
    row: {
        backgroundColor: "#111111",
        paddingHorizontal: 16,
        height: 46,
        flexDirection: "row",
        alignItems: "center",
    },
    description: { fontSize: 13, color: "#FFFFFF", fontWeight: "500" },
    separator: { height: 1, backgroundColor: "rgba(255,255,255,0.05)" },
    poweredContainer: { display: "none" },
};

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: "#000000" },
    header: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: 20,
        paddingTop: 12,
        paddingBottom: 16,
        gap: 16,
    },
    backBtn: {
        width: 32, height: 32, borderRadius: 16,
        backgroundColor: "rgba(255,255,255,0.07)",
        borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
        alignItems: "center", justifyContent: "center",
    },
    backArrow: { fontSize: 14, fontWeight: "700", color: "#FFFFFF" },
    headerTitle: { fontSize: 18, fontWeight: "900", color: "#FFFFFF", letterSpacing: -0.5 },
    accent: { color: "#276EF1" },
    headerSub: { fontSize: 12, color: "#555", fontWeight: "500", marginTop: 2 },

    content: { paddingHorizontal: 20, flex: 1 },
    inputGroup: { flexDirection: "row", gap: 15, marginBottom: 0 },
    dotLineContainer: { alignItems: "center", width: 10, paddingTop: 26 },
    dotWhite: { width: 6, height: 6, borderRadius: 3, backgroundColor: "#fff" },
    dotBlue: { width: 6, height: 6, borderRadius: 1.2, backgroundColor: "#276EF1" },
    line: { width: 1, height: 34, backgroundColor: "rgba(255,255,255,0.1)", marginVertical: 4 },

    searchWrapper: { flex: 1 },
    inputLabel: { fontSize: 8, fontWeight: "900", color: "#333", letterSpacing: 1.5, marginBottom: 5 },
    textInput: {
        fontSize: 13,
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 10,
        height: 44,
        paddingHorizontal: 12,
        fontWeight: "600",
        color: "#FFFFFF",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
    },
    overlay: {
        position: "absolute",
        top: 0, left: 0, right: 0, bottom: 0,
    },
    searchPanel: {
        backgroundColor: "rgba(0,0,0,0.85)",
        borderRadius: 20,
        padding: 16,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.5,
        shadowRadius: 20,
        elevation: 10,
    },
    pickupMarker: {
        width: 14,
        height: 14,
        borderRadius: 7,
        backgroundColor: "#FFFFFF",
        borderWidth: 3,
        borderColor: "#276EF1",
    },
    carMarker: {
        backgroundColor: "rgba(0,0,0,0.85)",
        borderRadius: 20,
        padding: 4,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.2)",
    }
});
