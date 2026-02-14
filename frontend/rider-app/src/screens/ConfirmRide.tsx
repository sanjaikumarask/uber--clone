import React, { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Dimensions } from "react-native";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import { api } from "../services/api";

const { width, height } = Dimensions.get("window");

export default function ConfirmRideScreen({ navigation, route }: any) {
    const { destination } = route.params;
    const [loading, setLoading] = useState(false);

    const handleConfirmRide = async () => {
        setLoading(true);
        try {
            // Hardcoded pickup for demo (User's current location from previous screen ideally)
            // Ideally we pass pickup location too. For now let's assume valid pickup.
            const pickup = { lat: 13.0827, lng: 80.2707 }; // Chennai Central example

            const payload = {
                pickup_lat: pickup.lat,
                pickup_lng: pickup.lng,
                drop_lat: destination.lat,
                drop_lng: destination.lng,
            };

            const res = await api.post("/rides/request/", payload);
            console.log("Ride Created:", res.data);

            Alert.alert("Success", "Ride request sent! Searching for drivers...");

            // Navigate to Tracking Screen
            navigation.replace("RideTracking", { rideId: res.data.ride_id });
        } catch (err: any) {
            console.error("Ride request failed", err.response?.data);
            Alert.alert("Error", "Failed to request ride. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <View style={styles.container}>
            <MapView
                provider={PROVIDER_GOOGLE}
                style={styles.map}
                initialRegion={{
                    latitude: destination.lat,
                    longitude: destination.lng,
                    latitudeDelta: 0.05,
                    longitudeDelta: 0.05,
                }}
            >
                <Marker
                    coordinate={{ latitude: destination.lat, longitude: destination.lng }}
                    title={destination.description}
                />
            </MapView>

            <View style={styles.panel}>
                <Text style={styles.addressTitle}>Destination</Text>
                <Text style={styles.address}>{destination.description}</Text>

                <View style={styles.fareContainer}>
                    <Text style={styles.fareText}>Estimated Fare</Text>
                    <Text style={styles.price}>₹250 - ₹300</Text>
                </View>

                <TouchableOpacity
                    style={styles.confirmButton}
                    onPress={handleConfirmRide}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <Text style={styles.confirmText}>Confirm Uber</Text>
                    )}
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    map: {
        flex: 1,
    },
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
    },
    addressTitle: {
        fontSize: 14,
        color: "#666",
        marginBottom: 5,
    },
    address: {
        fontSize: 18,
        fontWeight: "bold",
        marginBottom: 20,
    },
    fareContainer: {
        flexDirection: "row",
        justifyContent: "space-between",
        marginBottom: 20,
        paddingBottom: 20,
        borderBottomWidth: 1,
        borderBottomColor: "#eee",
    },
    fareText: {
        fontSize: 16,
        color: "#333",
    },
    price: {
        fontSize: 16,
        fontWeight: "bold",
    },
    confirmButton: {
        backgroundColor: "#000",
        padding: 16,
        borderRadius: 8,
        alignItems: "center",
    },
    confirmText: {
        color: "#fff",
        fontSize: 18,
        fontWeight: "bold",
    },
});
