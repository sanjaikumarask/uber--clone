
import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { api } from "../services/api";

interface SupportTicket {
    id: number;
    reason: string;
    description: string;
    status: "OPEN" | "RESOLVED" | "REJECTED";
    created_at: string;
    resolution_note?: string;
}

export default function SupportScreen() {
    const navigation = useNavigation() as any;
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchTickets();
    }, []);

    const fetchTickets = async () => {
        try {
            const res = await api.get("/supports/tickets/");
            if (Array.isArray(res.data)) {
                setTickets(res.data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const renderItem = ({ item }: { item: SupportTicket }) => (
        <View style={styles.card}>
            <View style={styles.header}>
                <Text style={styles.reason}>{item.reason.replace("_", " ")}</Text>
                <View style={[
                    styles.badge,
                    { backgroundColor: item.status === "OPEN" ? "#facc15" : item.status === "RESOLVED" ? "#22c55e" : "#ef4444" }
                ]}>
                    <Text style={styles.statusText}>{item.status}</Text>
                </View>
            </View>

            <Text style={styles.date}>{new Date(item.created_at).toLocaleDateString()}</Text>
            <Text style={styles.desc}>"{item.description}"</Text>

            {item.resolution_note && (
                <View style={styles.response}>
                    <Text style={styles.responseTitle}>Support Response:</Text>
                    <Text style={styles.responseText}>{item.resolution_note}</Text>
                </View>
            )}
        </View>
    );

    return (
        <View style={styles.container}>
            <View style={styles.navBar}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
                    <Text style={styles.backText}>←</Text>
                </TouchableOpacity>
                <Text style={styles.title}>Support Tickets</Text>
            </View>

            {loading ? (
                <ActivityIndicator size="large" color="#fff" style={{ marginTop: 50 }} />
            ) : tickets.length === 0 ? (
                <View style={styles.empty}>
                    <Text style={styles.emptyText}>No support tickets found.</Text>
                </View>
            ) : (
                <FlatList
                    data={tickets}
                    keyExtractor={item => item.id.toString()}
                    renderItem={renderItem}
                    contentContainerStyle={styles.list}
                />
            )}
        </View>
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
    list: {
        padding: 20,
    },
    empty: {
        marginTop: 50,
        alignItems: "center"
    },
    emptyText: {
        color: "#666",
        fontSize: 16
    },
    card: {
        backgroundColor: "#161616",
        padding: 15,
        borderRadius: 10,
        marginBottom: 15,
        borderWidth: 1,
        borderColor: "#333"
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 5
    },
    reason: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "bold",
        textTransform: "capitalize"
    },
    badge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12
    },
    statusText: {
        color: "#000",
        fontSize: 10,
        fontWeight: "bold"
    },
    date: {
        color: "#666",
        fontSize: 12,
        marginBottom: 8
    },
    desc: {
        color: "#ccc",
        fontStyle: "italic",
        marginBottom: 10
    },
    response: {
        backgroundColor: "#222",
        padding: 10,
        borderRadius: 6,
        marginTop: 5
    },
    responseTitle: {
        color: "#fff",
        fontWeight: "bold",
        fontSize: 12,
        marginBottom: 2
    },
    responseText: {
        color: "#ddd",
        fontSize: 12
    }
});
