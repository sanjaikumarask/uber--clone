import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, TextInput } from "react-native";
import { api } from "../services/api";

export default function RideTrackingScreen({ route, navigation }: any) {
    const { rideId } = route.params || {};
    const [rideStatus, setRideStatus] = useState("ASSIGNED");
    const [otp, setOtp] = useState("");

    useEffect(() => {
        fetchRideDetails();
    }, []);

    async function fetchRideDetails() {
        try {
            const { data } = await api.get(`/rides/${rideId}/`);
            setRideStatus(data.status);
        } catch (err) {
            console.error("Failed to fetch ride details");
        }
    }

    async function markArrived() {
        try {
            await api.post(`/rides/${rideId}/arrived/`);
            setRideStatus("ARRIVED");
            Alert.alert("Success", "Marked as arrived");
        } catch (err: any) {
            Alert.alert("Error", "Failed to mark arrived");
        }
    }

    async function startRide() {
        if (!otp) {
            Alert.alert("Error", "Please enter OTP");
            return;
        }
        try {
            await api.post(`/rides/${rideId}/start/`, { otp });
            setRideStatus("ONGOING");
            Alert.alert("Success", "Ride started!");
        } catch (err: any) {
            Alert.alert("Error", "Invalid OTP or failed to start ride");
        }
    }

    async function completeRide() {
        try {
            await api.post(`/rides/${rideId}/complete/`);
            Alert.alert("Success", "Ride completed!");
            navigation.replace("Home");
        } catch (err: any) {
            Alert.alert("Error", "Failed to complete ride");
        }
    }

    async function markNoShow() {
        try {
            await api.post(`/rides/${rideId}/no-show/`);
            Alert.alert("No Show", "Rider marked as no-show");
            navigation.replace("Home");
        } catch (err: any) {
            Alert.alert("Error", "Failed to mark no-show");
        }
    }

    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <Text style={styles.title}>Ride #{rideId}</Text>
                <View style={styles.statusBadge}>
                    <Text style={styles.statusText}>{rideStatus}</Text>
                </View>
            </View>

            <View style={styles.card}>
                {rideStatus === "ASSIGNED" && (
                    <>
                        <Text style={styles.instruction}>Navigate to pickup location</Text>
                        <TouchableOpacity style={styles.btn} onPress={markArrived}>
                            <Text style={styles.btnText}>Mark as Arrived</Text>
                        </TouchableOpacity>
                    </>
                )}

                {rideStatus === "ARRIVED" && (
                    <>
                        <Text style={styles.instruction}>Enter OTP from rider to start</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="Enter OTP"
                            value={otp}
                            onChangeText={setOtp}
                            keyboardType="number-pad"
                            maxLength={6}
                        />
                        <TouchableOpacity style={styles.btn} onPress={startRide}>
                            <Text style={styles.btnText}>Start Ride</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.btnSecondary} onPress={markNoShow}>
                            <Text style={styles.btnSecondaryText}>Mark No-Show</Text>
                        </TouchableOpacity>
                    </>
                )}

                {rideStatus === "ONGOING" && (
                    <>
                        <Text style={styles.instruction}>Drive to destination</Text>
                        <TouchableOpacity style={styles.btn} onPress={completeRide}>
                            <Text style={styles.btnText}>Complete Ride</Text>
                        </TouchableOpacity>
                    </>
                )}
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
        marginBottom: 30,
    },
    title: {
        fontSize: 24,
        fontWeight: "bold",
        marginBottom: 10,
    },
    statusBadge: {
        backgroundColor: "#007AFF",
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
        alignSelf: "flex-start",
    },
    statusText: {
        color: "#fff",
        fontSize: 14,
        fontWeight: "600",
    },
    card: {
        backgroundColor: "#fff",
        padding: 25,
        borderRadius: 16,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    instruction: {
        fontSize: 16,
        color: "#666",
        marginBottom: 20,
        textAlign: "center",
    },
    input: {
        borderWidth: 1,
        borderColor: "#ddd",
        padding: 15,
        borderRadius: 8,
        marginBottom: 15,
        fontSize: 18,
        textAlign: "center",
        letterSpacing: 5,
    },
    btn: {
        backgroundColor: "#000",
        padding: 16,
        borderRadius: 10,
        alignItems: "center",
        marginBottom: 10,
    },
    btnText: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "600",
    },
    btnSecondary: {
        backgroundColor: "#fff",
        padding: 16,
        borderRadius: 10,
        alignItems: "center",
        borderWidth: 1,
        borderColor: "#FF3B30",
    },
    btnSecondaryText: {
        color: "#FF3B30",
        fontSize: 16,
        fontWeight: "600",
    },
});
