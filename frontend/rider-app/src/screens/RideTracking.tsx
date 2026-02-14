import React, { useEffect, useState, useRef } from "react";
import { View, Text, StyleSheet, ActivityIndicator, Alert, Dimensions, TouchableOpacity } from "react-native";
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from "react-native-maps";
import { api, WS_URL } from "../services/api";
import { Storage } from "../services/storage";
import { useAuth } from "../contexts/AuthContext";

const { width, height } = Dimensions.get("window");

export default function RideTrackingScreen({ navigation, route }: any) {
    const { rideId } = route.params;
    const [ride, setRide] = useState<any>(null);
    const [status, setStatus] = useState("SEARCHING");
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const mapRef = useRef<MapView>(null);
    const { isAuthenticated } = useAuth(); // Just to access context if needed

    useEffect(() => {
        let ws: WebSocket | null = null;

        const setup = async () => {
            // Initial Fetch
            fetchRideDetails();

            // Get Token
            const token = await Storage.getToken();
            if (!token) {
                console.error("No token found for WS");
                return;
            }

            // Setup WebSocket with Token
            ws = new WebSocket(`${WS_URL}/rides/${rideId}/?token=${token}`);
            ws.onopen = () => console.log("Ride WS Connected");
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                console.log("WS Message:", data);
                if (data.type === "ride_update" || data.type === "WS_CONNECTED") {
                    const rideData = data.payload?.ride || data.ride;
                    if (rideData) {
                        setRide(rideData);
                        setStatus(rideData.status);
                    }
                }
            };
            ws.onerror = (e) => console.log("WS Error", e);
            ws.onclose = () => console.log("WS Closed");

            setSocket(ws);
        };

        setup();

        return () => {
            if (ws) ws.close();
        };
    }, [rideId]);

    const fetchRideDetails = async () => {
        try {
            const res = await api.get(`/rides/${rideId}/`);
            setRide(res.data);
            setStatus(res.data.status);
        } catch (err) {
            console.error("Fetch ride failed", err);
        }
    };

    const getStatusMessage = () => {
        switch (status) {
            case "SEARCHING": return "Finding you a driver...";
            case "OFFERED": return "Contacting drivers...";
            case "ASSIGNED": return "Driver is on the way!";
            case "ARRIVED": return "Driver has arrived!";
            case "ONGOING": return "Ride in progress";
            case "COMPLETED": return "Ride completed";
            case "non_field_errors": return "Ride Cancelled";
            default: return status;
        }
    };

    if (!ride) {
        return (
            <View style={styles.center}>
                <ActivityIndicator size="large" color="#000" />
                <Text style={{ marginTop: 10 }}>Loading ride details...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <MapView
                ref={mapRef}
                provider={PROVIDER_GOOGLE}
                style={styles.map}
                initialRegion={{
                    latitude: ride.pickup_lat,
                    longitude: ride.pickup_lng,
                    latitudeDelta: 0.05,
                    longitudeDelta: 0.05,
                }}
            >
                <Marker
                    coordinate={{ latitude: ride.pickup_lat, longitude: ride.pickup_lng }}
                    title="Pickup"
                    pinColor="green"
                />
                <Marker
                    coordinate={{ latitude: ride.drop_lat, longitude: ride.drop_lng }}
                    title="Dropoff"
                    pinColor="red"
                />
                {/* {ride.planned_route_polyline && (
                    <Polyline
                        coordinates={decodePolyline(ride.planned_route_polyline)}
                        strokeWidth={4}
                        strokeColor="#000"
                    />
                )} */}
            </MapView>

            <View style={styles.panel}>
                <Text style={styles.statusTitle}>{getStatusMessage()}</Text>
                <ActivityIndicator
                    size="small"
                    color="#000"
                    animating={status === "SEARCHING" || status === "OFFERED"}
                    style={{ marginBottom: 10 }}
                />

                <View style={styles.infoRow}>
                    <Text>Ride ID: {ride.id}</Text>
                </View>

                {ride.driver && (
                    <View style={styles.driverInfo}>
                        <Text style={styles.driverName}>
                            Driver: {ride.driver.user?.first_name ? `${ride.driver.user.first_name} ${ride.driver.user.last_name || ""}`.trim() : "Unknown Driver"}
                        </Text>
                        <Text>
                            Vehicle: {ride.driver.vehicle_model || "Unknown Model"}{" "}
                            {ride.driver.vehicle_number ? `(${ride.driver.vehicle_number})` : ""}
                        </Text>
                    </View>
                )}

                {ride.otp_code && (
                    <Text style={styles.otp}>OTP: {ride.otp_code}</Text>
                )}
            </View>
        </View>
    );
}

// Helper to decode Google Polyline (simplified)
// You might want to install @mapbox/polyline later
const decodePolyline = (t: string) => {
    // Placeholder: returning start/end points if decoding fails or isn't implemented
    // Real implementation needed for actual path drawing
    return [];
};

const styles = StyleSheet.create({
    container: { flex: 1 },
    center: { flex: 1, justifyContent: "center", alignItems: "center" },
    map: { flex: 1 },
    panel: {
        backgroundColor: "white",
        padding: 20,
        borderTopLeftRadius: 20,
        borderTopRightRadius: 20,
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        elevation: 10,
        alignItems: "center"
    },
    statusTitle: {
        fontSize: 20,
        fontWeight: "bold",
        marginBottom: 10,
    },
    infoRow: {
        marginBottom: 10,
    },
    driverInfo: {
        marginTop: 10,
        padding: 10,
        backgroundColor: "#f9f9f9",
        borderRadius: 8,
        width: "100%",
    },
    driverName: {
        fontWeight: "bold",
        fontSize: 16,
    },
    otp: {
        fontSize: 24,
        fontWeight: "bold",
        marginTop: 15,
        letterSpacing: 5,
    }
});
