import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { api } from "../services/api";

export default function RideOfferScreen({ route, navigation }: any) {
    const { rideId, pickup, dropoff } = route.params || {};

    async function handleAccept() {
        try {
            await api.post(`/rides/${rideId}/accept/`);
            Alert.alert("Success", "Ride accepted!");
            navigation.replace("RideTracking", { rideId });
        } catch (err: any) {
            Alert.alert("Error", "Failed to accept ride");
        }
    }

    async function handleReject() {
        try {
            await api.post(`/rides/${rideId}/reject/`);
            Alert.alert("Rejected", "Ride rejected");
            navigation.goBack();
        } catch (err: any) {
            Alert.alert("Error", "Failed to reject ride");
        }
    }

    return (
        <View style={styles.container}>
            <View style={styles.card}>
                <Text style={styles.title}>New Ride Request</Text>

                <View style={styles.section}>
                    <Text style={styles.label}>Pickup:</Text>
                    <Text style={styles.value}>{pickup || "Location A"}</Text>
                </View>

                <View style={styles.section}>
                    <Text style={styles.label}>Dropoff:</Text>
                    <Text style={styles.value}>{dropoff || "Location B"}</Text>
                </View>

                <View style={styles.section}>
                    <Text style={styles.label}>Ride ID:</Text>
                    <Text style={styles.value}>#{rideId}</Text>
                </View>

                <View style={styles.buttonRow}>
                    <TouchableOpacity style={styles.rejectBtn} onPress={handleReject}>
                        <Text style={styles.rejectText}>Reject</Text>
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.acceptBtn} onPress={handleAccept}>
                        <Text style={styles.acceptText}>Accept</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#f5f5f5",
        justifyContent: "center",
        padding: 20,
    },
    card: {
        backgroundColor: "#fff",
        padding: 25,
        borderRadius: 16,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 5,
    },
    title: {
        fontSize: 24,
        fontWeight: "bold",
        marginBottom: 25,
        textAlign: "center",
    },
    section: {
        marginBottom: 20,
    },
    label: {
        fontSize: 14,
        color: "#666",
        marginBottom: 5,
    },
    value: {
        fontSize: 18,
        fontWeight: "600",
    },
    buttonRow: {
        flexDirection: "row",
        gap: 15,
        marginTop: 30,
    },
    rejectBtn: {
        flex: 1,
        backgroundColor: "#FF3B30",
        padding: 16,
        borderRadius: 10,
        alignItems: "center",
    },
    rejectText: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "600",
    },
    acceptBtn: {
        flex: 1,
        backgroundColor: "#34C759",
        padding: 16,
        borderRadius: 10,
        alignItems: "center",
    },
    acceptText: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "600",
    },
});
