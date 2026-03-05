import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, FlatList, ActivityIndicator } from "react-native";
import { api } from "../services/api";

export default function RideHistoryScreen({ navigation }: any) {
    const [rides, setRides] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHistory();
    }, []);

    async function fetchHistory() {
        try {
            setLoading(true);
            const res = await api.get("drivers/ride-history/");
            setRides(res.data || []);
        } catch (err) {
            console.error("Failed to fetch ride history", err);
        } finally {
            setLoading(false);
        }
    }

    const renderRideItem = ({ item }: { item: any }) => {
        const isCompleted = item.status === "COMPLETED";
        const date = new Date(item.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        return (
            <TouchableOpacity
                style={styles.rideCard}
                onPress={() => navigation.navigate("RideTracking", { rideId: item.id })}
            >
                <View style={styles.rideHeader}>
                    <Text style={styles.dateText}>{date}</Text>
                    <View style={[styles.statusBadge, { backgroundColor: isCompleted ? "#E8F5E9" : "#FFEBEE" }]}>
                        <Text style={[styles.statusText, { color: isCompleted ? "#2E7D32" : "#C62828" }]}>
                            {item.status}
                        </Text>
                    </View>
                </View>

                <View style={styles.locationContainer}>
                    <View style={styles.dotContainer}>
                        <View style={styles.dot} />
                        <View style={styles.line} />
                        <View style={[styles.dot, { backgroundColor: "#000" }]} />
                    </View>
                    <View style={styles.addressContainer}>
                        <Text style={styles.addressText} numberOfLines={1}>{item.pickup_address || "Pickup Location"}</Text>
                        <View style={{ height: 15 }} />
                        <Text style={styles.addressText} numberOfLines={1}>{item.drop_address || "Drop Location"}</Text>
                    </View>
                </View>

                <View style={styles.footer}>
                    <Text style={styles.vehicleText}>{item.vehicle_type?.toUpperCase()}</Text>
                    <Text style={styles.fareText}>₹{parseFloat(item.final_fare || item.base_fare).toFixed(2)}</Text>
                </View>
            </TouchableOpacity>
        );
    };

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
                <Text style={styles.title}>Ride History</Text>
                <View style={{ width: 40 }} />
            </View>

            <FlatList
                data={rides}
                keyExtractor={(item) => item.id.toString()}
                renderItem={renderRideItem}
                contentContainerStyle={{ paddingBottom: 40 }}
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyText}>No rides found</Text>
                    </View>
                }
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#f8f8f8",
        padding: 20,
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
        marginBottom: 20,
    },
    backText: {
        fontSize: 16,
        color: "#007AFF",
    },
    title: {
        fontSize: 22,
        fontWeight: "bold",
    },
    rideCard: {
        backgroundColor: "#fff",
        borderRadius: 15,
        padding: 15,
        marginBottom: 15,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    rideHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 15,
    },
    dateText: {
        fontSize: 14,
        color: "#666",
        fontWeight: "600",
    },
    statusBadge: {
        paddingVertical: 4,
        paddingHorizontal: 10,
        borderRadius: 12,
    },
    statusText: {
        fontSize: 11,
        fontWeight: "bold",
    },
    locationContainer: {
        flexDirection: "row",
        marginBottom: 15,
    },
    dotContainer: {
        alignItems: "center",
        width: 20,
        marginRight: 10,
        paddingVertical: 5,
    },
    dot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: "#34C759",
    },
    line: {
        width: 1,
        flex: 1,
        backgroundColor: "#ccc",
        marginVertical: 4,
    },
    addressContainer: {
        flex: 1,
    },
    addressText: {
        fontSize: 14,
        color: "#333",
    },
    footer: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        borderTopWidth: 1,
        borderTopColor: "#eee",
        paddingTop: 12,
    },
    vehicleText: {
        fontSize: 12,
        color: "#999",
        fontWeight: "bold",
    },
    fareText: {
        fontSize: 18,
        fontWeight: "bold",
        color: "#000",
    },
    emptyState: {
        padding: 100,
        alignItems: "center",
    },
    emptyText: {
        color: "#999",
    },
});
