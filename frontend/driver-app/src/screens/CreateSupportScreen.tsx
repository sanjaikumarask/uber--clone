
import React, { useState } from "react";
import { View, Text, StyleSheet, TextInput, TouchableOpacity, Alert, ScrollView } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import { api } from "../services/api";

const REASONS = [
    { label: "Rider Misconduct", value: "DRIVER_MISCONDUCT" }, // Reuse same backend choices
    { label: "Route Issue", value: "ROUTE_DEVIATION" },
    { label: "Other", value: "OTHER" },
];

export default function CreateSupportScreen() {
    const navigation = useNavigation() as any;
    const route = useRoute() as any;
    const { rideId } = route.params || {};

    const [reason, setReason] = useState(REASONS[0].value);
    const [description, setDescription] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        if (!rideId) {
            Alert.alert("Error", "Ride ID missing.");
            return;
        }
        if (!description.trim()) {
            Alert.alert("Error", "Please provide a description.");
            return;
        }

        setLoading(true);
        try {
            await api.post(`/supports/rides/${rideId}/tickets/`, {
                reason,
                description
            });
            Alert.alert("Success", "Support ticket created. We will get back to you soon.");
            navigation.goBack();
        } catch (err: any) {
            Alert.alert("Error", err.response?.data?.error || "Failed to create ticket.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <ScrollView style={styles.container}>
            <View style={styles.navBar}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
                    <Text style={styles.backText}>←</Text>
                </TouchableOpacity>
                <Text style={styles.title}>Raise an Issue</Text>
            </View>

            <View style={styles.content}>
                <Text style={styles.rideId}>Reporting Issue for Ride #{rideId}</Text>

                <Text style={styles.label}>Reason</Text>
                <View style={styles.reasonsGrid}>
                    {REASONS.map((r) => (
                        <TouchableOpacity
                            key={r.value}
                            style={[styles.reasonBtn, reason === r.value && styles.reasonBtnActive]}
                            onPress={() => setReason(r.value)}
                        >
                            <Text style={[styles.reasonText, reason === r.value && styles.reasonTextActive]}>
                                {r.label}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </View>

                <Text style={styles.label}>Describe your problem</Text>
                <TextInput
                    style={styles.input}
                    placeholder="Provide details about what happened..."
                    placeholderTextColor="#666"
                    multiline
                    numberOfLines={6}
                    value={description}
                    onChangeText={setDescription}
                />

                <TouchableOpacity
                    style={[styles.submitBtn, loading && { opacity: 0.5 }]}
                    onPress={handleSubmit}
                    disabled={loading}
                >
                    <Text style={styles.submitBtnText}>{loading ? "Submitting..." : "Submit Ticket"}</Text>
                </TouchableOpacity>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#000",
    },
    navBar: {
        flexDirection: "row",
        alignItems: "center",
        paddingTop: 50,
        paddingBottom: 20,
        paddingHorizontal: 20,
        borderBottomWidth: 1,
        borderBottomColor: "#222"
    },
    backBtn: {
        padding: 5,
        marginRight: 15
    },
    backText: {
        color: "#fff",
        fontSize: 24,
        fontWeight: "bold"
    },
    title: {
        color: "#fff",
        fontSize: 20,
        fontWeight: "bold"
    },
    content: {
        padding: 20,
    },
    rideId: {
        color: "#aaa",
        marginBottom: 20,
        fontSize: 14
    },
    label: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "bold",
        marginBottom: 10
    },
    reasonsGrid: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: 10,
        marginBottom: 25
    },
    reasonBtn: {
        backgroundColor: "#161616",
        paddingHorizontal: 15,
        paddingVertical: 10,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "#333"
    },
    reasonBtnActive: {
        backgroundColor: "#fff",
        borderColor: "#fff"
    },
    reasonText: {
        color: "#aaa",
        fontSize: 14
    },
    reasonTextActive: {
        color: "#000",
        fontWeight: "bold"
    },
    input: {
        backgroundColor: "#161616",
        color: "#fff",
        borderRadius: 12,
        padding: 15,
        textAlignVertical: "top",
        fontSize: 16,
        marginBottom: 30,
        borderWidth: 1,
        borderColor: "#333"
    },
    submitBtn: {
        backgroundColor: "#fff",
        padding: 18,
        borderRadius: 12,
        alignItems: "center"
    },
    submitBtnText: {
        color: "#000",
        fontSize: 18,
        fontWeight: "bold"
    }
});
