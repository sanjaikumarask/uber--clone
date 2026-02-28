import React, { useEffect, useState } from "react";
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity,
    ActivityIndicator, StatusBar, Platform
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL } from "../services/api";

interface SupportTicket {
    id: number;
    reason: string;
    description: string;
    status: "OPEN" | "RESOLVED" | "REJECTED";
    created_at: string;
    resolution_note?: string;
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
    OPEN: { bg: "rgba(245,158,11,0.15)", text: "#f59e0b" },
    RESOLVED: { bg: "rgba(34,197,94,0.15)", text: "#22c55e" },
    REJECTED: { bg: "rgba(239,68,68,0.15)", text: "#ef4444" },
};

export default function SupportScreen() {
    const navigation = useNavigation<any>();
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => { fetchTickets(); }, []);

    const fetchTickets = async () => {
        try {
            const token = await AsyncStorage.getItem("access_token");
            if (!token) return;
            const res = await fetch(`${API_URL}/supports/tickets/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            if (Array.isArray(data)) setTickets(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const renderItem = ({ item }: { item: SupportTicket }) => {
        const sc = STATUS_COLORS[item.status] || STATUS_COLORS.OPEN;
        return (
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <Text style={styles.reason}>
                        {item.reason.replace(/_/g, " ")}
                    </Text>
                    <View style={[styles.badge, { backgroundColor: sc.bg }]}>
                        <Text style={[styles.statusText, { color: sc.text }]}>{item.status}</Text>
                    </View>
                </View>

                <Text style={styles.date}>
                    {new Date(item.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                </Text>
                <Text style={styles.desc}>"{item.description}"</Text>

                {item.resolution_note && (
                    <View style={styles.response}>
                        <Text style={styles.responseTitle}>Support Response</Text>
                        <Text style={styles.responseText}>{item.resolution_note}</Text>
                    </View>
                )}
            </View>
        );
    };

    return (
        <View style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor="#000" />

            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn} activeOpacity={0.8}>
                    <Text style={styles.backArrow}>←</Text>
                </TouchableOpacity>
                <View style={{ flex: 1 }}>
                    <Text style={styles.headerTitle}>Support<Text style={styles.headerAccent}>.</Text></Text>
                    <Text style={styles.headerSub}>Your support tickets</Text>
                </View>
                <TouchableOpacity
                    style={styles.newBtn}
                    onPress={() => navigation.navigate("CreateSupport")}
                    activeOpacity={0.8}
                >
                    <Text style={styles.newBtnText}>+ New</Text>
                </TouchableOpacity>
            </View>

            {loading ? (
                <View style={styles.center}>
                    <ActivityIndicator size="large" color="#276EF1" />
                </View>
            ) : tickets.length === 0 ? (
                <View style={styles.empty}>
                    <Text style={styles.emptyEmoji}>🎧</Text>
                    <Text style={styles.emptyTitle}>No tickets yet</Text>
                    <Text style={styles.emptyText}>Create a ticket and we'll get back to you soon.</Text>
                    <TouchableOpacity
                        style={styles.createBtn}
                        onPress={() => navigation.navigate("CreateSupport")}
                        activeOpacity={0.85}
                    >
                        <Text style={styles.createBtnText}>Create Ticket</Text>
                    </TouchableOpacity>
                </View>
            ) : (
                <FlatList
                    data={tickets}
                    keyExtractor={item => item.id.toString()}
                    renderItem={renderItem}
                    contentContainerStyle={styles.list}
                    showsVerticalScrollIndicator={false}
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: "#000" },
    center: { flex: 1, justifyContent: "center", alignItems: "center" },

    header: {
        flexDirection: "row",
        alignItems: "center",
        paddingTop: Platform.OS === "ios" ? 60 : 48,
        paddingBottom: 20,
        paddingHorizontal: 20,
        gap: 14,
        borderBottomWidth: 1,
        borderBottomColor: "rgba(255,255,255,0.06)",
    },
    backBtn: {
        width: 40, height: 40, borderRadius: 20,
        backgroundColor: "rgba(255,255,255,0.07)",
        borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
        alignItems: "center", justifyContent: "center",
    },
    backArrow: { fontSize: 18, fontWeight: "700", color: "#fff" },
    headerTitle: { fontSize: 26, fontWeight: "900", color: "#fff", letterSpacing: -0.5 },
    headerAccent: { color: "#276EF1" },
    headerSub: { fontSize: 12, color: "#555", marginTop: 2, fontWeight: "500" },
    newBtn: {
        backgroundColor: "#276EF1",
        paddingHorizontal: 16, paddingVertical: 9,
        borderRadius: 20,
    },
    newBtnText: { color: "#fff", fontWeight: "800", fontSize: 13 },

    list: { padding: 20, gap: 12 },

    card: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 18,
        padding: 18,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
    },
    cardHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 8,
    },
    reason: {
        color: "#fff",
        fontSize: 15,
        fontWeight: "800",
        textTransform: "capitalize",
        flex: 1,
        marginRight: 10,
    },
    badge: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 10,
    },
    statusText: { fontSize: 11, fontWeight: "900", letterSpacing: 0.4 },
    date: { color: "#555", fontSize: 12, marginBottom: 10, fontWeight: "500" },
    desc: { color: "#A6A6A6", fontStyle: "italic", fontSize: 13, lineHeight: 18 },
    response: {
        backgroundColor: "rgba(255,255,255,0.05)",
        padding: 12,
        borderRadius: 10,
        marginTop: 12,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.07)",
    },
    responseTitle: { color: "#276EF1", fontWeight: "700", fontSize: 11, letterSpacing: 0.6, marginBottom: 4, textTransform: "uppercase" },
    responseText: { color: "#A6A6A6", fontSize: 13, lineHeight: 18 },

    empty: { flex: 1, justifyContent: "center", alignItems: "center", gap: 10, paddingHorizontal: 40 },
    emptyEmoji: { fontSize: 56, marginBottom: 8 },
    emptyTitle: { fontSize: 22, fontWeight: "900", color: "#fff" },
    emptyText: { fontSize: 14, color: "#555", textAlign: "center", lineHeight: 20 },
    createBtn: {
        marginTop: 16,
        backgroundColor: "#276EF1",
        paddingVertical: 16,
        paddingHorizontal: 36,
        borderRadius: 14,
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.4,
        shadowRadius: 12,
        elevation: 8,
    },
    createBtnText: { color: "#fff", fontWeight: "900", fontSize: 16 },
});
