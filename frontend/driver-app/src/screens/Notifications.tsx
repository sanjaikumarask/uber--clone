import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, FlatList, ActivityIndicator } from "react-native";
import { api } from "../services/api";

interface Notification {
    id: string;
    title: string;
    message: string;
    created_at: string;
    is_read: boolean;
}

export default function NotificationsScreen({ navigation }: any) {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchNotifications();
    }, []);

    async function fetchNotifications() {
        try {
            setLoading(true);
            const res = await api.get("/notifications/");
            setNotifications(res.data.results || res.data || []);
        } catch (err: any) {
            console.error("Failed to fetch notifications", err);
            // Don't show error for 401/404 - user might not be logged in yet
            if (err.response?.status !== 401 && err.response?.status !== 404) {
                console.error("Unexpected error:", err.response?.status);
            }
        } finally {
            setLoading(false);
        }
    }

    async function markAsRead(id: string) {
        try {
            await api.post(`/notifications/${id}/mark-read/`);
            setNotifications(prev =>
                prev.map(n => n.id === id ? { ...n, is_read: true } : n)
            );
        } catch (err) {
            console.error("Failed to mark as read", err);
        }
    }

    const renderNotification = ({ item }: { item: Notification }) => (
        <TouchableOpacity
            style={[styles.notificationCard, !item.is_read && styles.unread]}
            onPress={() => markAsRead(item.id)}
        >
            <View style={styles.notificationHeader}>
                <Text style={styles.notificationTitle}>{item.title}</Text>
                {!item.is_read && <View style={styles.unreadDot} />}
            </View>
            <Text style={styles.notificationMessage}>{item.message}</Text>
            <Text style={styles.notificationTime}>
                {new Date(item.created_at).toLocaleString()}
            </Text>
        </TouchableOpacity>
    );

    if (loading) {
        return (
            <View style={styles.center}>
                <ActivityIndicator size="large" color="#000" />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <Text style={styles.backText}>← Back</Text>
                </TouchableOpacity>
                <Text style={styles.title}>Notifications</Text>
                <View style={{ width: 40 }} />
            </View>

            {notifications.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyText}>No notifications yet</Text>
                </View>
            ) : (
                <FlatList
                    data={notifications}
                    renderItem={renderNotification}
                    keyExtractor={item => item.id}
                    contentContainerStyle={styles.listContent}
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#f5f5f5",
        paddingTop: 60,
    },
    center: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        paddingHorizontal: 20,
        marginBottom: 20,
    },
    backText: {
        fontSize: 16,
        color: "#007AFF",
    },
    title: {
        fontSize: 20,
        fontWeight: "bold",
    },
    listContent: {
        paddingHorizontal: 20,
    },
    notificationCard: {
        backgroundColor: "#fff",
        padding: 15,
        borderRadius: 12,
        marginBottom: 12,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    unread: {
        backgroundColor: "#E3F2FD",
        borderLeftWidth: 4,
        borderLeftColor: "#007AFF",
    },
    notificationHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 8,
    },
    notificationTitle: {
        fontSize: 16,
        fontWeight: "600",
        flex: 1,
    },
    unreadDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: "#007AFF",
    },
    notificationMessage: {
        fontSize: 14,
        color: "#666",
        marginBottom: 8,
    },
    notificationTime: {
        fontSize: 12,
        color: "#999",
    },
    emptyState: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        padding: 40,
    },
    emptyText: {
        fontSize: 16,
        color: "#999",
    },
});
