import React, { useState } from "react";
import {
    View, Text, StyleSheet, TextInput, TouchableOpacity,
    Alert, ActivityIndicator, StatusBar, Platform,
    KeyboardAvoidingView, ScrollView
} from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL } from "../services/api";

const REASONS = [
    { label: "Overcharged", value: "OVERCHARGED", emoji: "💸" },
    { label: "Driver Misconduct", value: "DRIVER_MISCONDUCT", emoji: "🚫" },
    { label: "No Show", value: "NO_SHOW_DISPUTE", emoji: "🕐" },
    { label: "Route Deviation", value: "ROUTE_DEVIATION", emoji: "🗺️" },
    { label: "Other", value: "OTHER", emoji: "💬" },
];

export default function CreateSupportScreen() {
    const navigation = useNavigation<any>();
    const route = useRoute();
    const { rideId } = (route.params as any) || {};

    const [reason, setReason] = useState("OTHER");
    const [description, setDescription] = useState("");
    const [loading, setLoading] = useState(false);
    const [focused, setFocused] = useState(false);

    const handleSubmit = async () => {
        if (!rideId) { Alert.alert("Error", "No ride ID associated"); return; }
        if (!description.trim()) { Alert.alert("Error", "Please provide a description"); return; }

        setLoading(true);
        try {
            const token = await AsyncStorage.getItem("access_token");
            const res = await fetch(`${API_URL}/supports/rides/${rideId}/ticket/`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ reason, description }),
            });
            const data = await res.json();
            if (res.ok) {
                Alert.alert("Ticket Submitted ✓", "We'll get back to you shortly.", [
                    { text: "OK", onPress: () => navigation.goBack() }
                ]);
            } else {
                Alert.alert("Error", data.error || "Failed to create ticket");
            }
        } catch {
            Alert.alert("Error", "Network error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.root}
            behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
            <StatusBar barStyle="light-content" backgroundColor="#000" />
            <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
                        <Text style={styles.backArrow}>←</Text>
                    </TouchableOpacity>
                    <View>
                        <Text style={styles.headerTitle}>Report Issue<Text style={styles.accent}>.</Text></Text>
                        {rideId && <Text style={styles.headerSub}>Ride #{rideId}</Text>}
                    </View>
                </View>

                {/* Section: Reason */}
                <View style={styles.section}>
                    <Text style={styles.sectionLabel}>WHAT HAPPENED?</Text>
                    <View style={styles.reasonGrid}>
                        {REASONS.map(r => {
                            const active = reason === r.value;
                            return (
                                <TouchableOpacity
                                    key={r.value}
                                    style={[styles.reasonChip, active && styles.reasonChipActive]}
                                    onPress={() => setReason(r.value)}
                                    activeOpacity={0.8}
                                >
                                    <Text style={styles.reasonEmoji}>{r.emoji}</Text>
                                    <Text style={[styles.reasonLabel, active && styles.reasonLabelActive]}>
                                        {r.label}
                                    </Text>
                                </TouchableOpacity>
                            );
                        })}
                    </View>
                </View>

                {/* Section: Description */}
                <View style={styles.section}>
                    <Text style={styles.sectionLabel}>DESCRIBE THE ISSUE</Text>
                    <TextInput
                        style={[styles.textarea, focused && styles.textareaFocused]}
                        multiline
                        numberOfLines={5}
                        placeholder="Tell us what happened in detail..."
                        placeholderTextColor="#444"
                        value={description}
                        onChangeText={setDescription}
                        textAlignVertical="top"
                        selectionColor="#276EF1"
                        onFocus={() => setFocused(true)}
                        onBlur={() => setFocused(false)}
                    />
                </View>

                {/* Submit */}
                <TouchableOpacity
                    style={[styles.submitBtn, loading && styles.disabled]}
                    onPress={handleSubmit}
                    disabled={loading}
                    activeOpacity={0.85}
                >
                    {loading ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <Text style={styles.submitText}>Submit Ticket</Text>
                    )}
                </TouchableOpacity>

                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.cancelBtn}>
                    <Text style={styles.cancelText}>Cancel</Text>
                </TouchableOpacity>
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: "#000" },
    scroll: { padding: 24, paddingBottom: 48 },

    header: {
        flexDirection: "row",
        alignItems: "flex-start",
        gap: 16,
        paddingTop: Platform.OS === "ios" ? 36 : 16,
        marginBottom: 36,
    },
    backBtn: {
        width: 40, height: 40, borderRadius: 20,
        backgroundColor: "rgba(255,255,255,0.07)",
        borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
        alignItems: "center", justifyContent: "center",
        marginTop: 2,
    },
    backArrow: { fontSize: 18, fontWeight: "700", color: "#fff" },
    headerTitle: { fontSize: 30, fontWeight: "900", color: "#fff", letterSpacing: -0.8 },
    accent: { color: "#276EF1" },
    headerSub: { fontSize: 13, color: "#555", marginTop: 4, fontWeight: "500" },

    section: { marginBottom: 28 },
    sectionLabel: {
        fontSize: 11, fontWeight: "700", color: "#555",
        letterSpacing: 1.2, marginBottom: 14,
    },

    reasonGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
    reasonChip: {
        flexDirection: "row",
        alignItems: "center",
        gap: 6,
        paddingVertical: 10,
        paddingHorizontal: 14,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
        backgroundColor: "rgba(255,255,255,0.04)",
    },
    reasonChipActive: {
        backgroundColor: "rgba(39,110,241,0.12)",
        borderColor: "#276EF1",
    },
    reasonEmoji: { fontSize: 16 },
    reasonLabel: { fontSize: 13, color: "#A6A6A6", fontWeight: "600" },
    reasonLabelActive: { color: "#276EF1", fontWeight: "800" },

    textarea: {
        backgroundColor: "rgba(255,255,255,0.04)",
        color: "#fff",
        borderRadius: 16,
        padding: 18,
        height: 140,
        borderWidth: 1.5,
        borderColor: "rgba(255,255,255,0.1)",
        fontSize: 15,
        fontWeight: "500",
    },
    textareaFocused: {
        borderColor: "#276EF1",
        backgroundColor: "rgba(39,110,241,0.05)",
    },

    submitBtn: {
        backgroundColor: "#276EF1",
        paddingVertical: 18,
        borderRadius: 14,
        alignItems: "center",
        marginBottom: 14,
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.4,
        shadowRadius: 16,
        elevation: 10,
    },
    disabled: { opacity: 0.65 },
    submitText: { color: "#fff", fontWeight: "900", fontSize: 17 },

    cancelBtn: { paddingVertical: 14, alignItems: "center" },
    cancelText: { color: "#444", fontWeight: "600", fontSize: 15 },
});
