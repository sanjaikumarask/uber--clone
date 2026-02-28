import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, FlatList, RefreshControl, ActivityIndicator, Alert } from "react-native";
import { api } from "../services/api";
import { DriverIncentive, DriverIncentiveEarning } from "../services/driverIncentiveService";

export default function IncentivesScreen() {
    const [incentives, setIncentives] = useState<DriverIncentive[]>([]);
    const [earnings, setEarnings] = useState<DriverIncentiveEarning[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = async () => {
        try {
            const [incentivesRes, earningsRes] = await Promise.all([
                api.get("driver-incentives/incentives/"),
                api.get("driver-incentives/earnings/"),
            ]);

            const incentivesData = incentivesRes.data.results || incentivesRes.data || [];
            const earningsData = earningsRes.data.results || earningsRes.data || [];

            console.log("[Incentives] Data retrieved:", incentivesData);

            setIncentives(incentivesData);
            setEarnings(earningsData);
        } catch (error) {
            console.error("Failed to fetch incentives", error);
            Alert.alert("Error", "Failed to load incentives.");
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const onRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const renderIncentive = ({ item }: { item: DriverIncentive }) => {
        const getConditionText = () => {
            if (item.type === "STREAK") {
                return `Requires ${item.condition.rides_required || 0} consecutive rides`;
            }
            if (item.type === "PEAK") {
                return `Peak Hour: ${item.condition.start_hour}:00 - ${item.condition.end_hour}:00`;
            }
            return item.description;
        };

        return (
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <Text style={styles.cardTitle}>{item.title}</Text>
                    <Text style={styles.bonusBadge}>+₹{item.reward_amount}</Text>
                </View>
                <Text style={styles.description}>{item.description}</Text>
                <View style={styles.detailsRow}>
                    <Text style={styles.detailText}>
                        {getConditionText()}
                    </Text>
                    {item.current_progress !== undefined && item.type === "STREAK" && (
                        <Text style={[styles.detailText, { color: "#2E7D32", fontWeight: "bold" }]}>
                            (Progress: {item.current_progress}/{item.condition.rides_required})
                        </Text>
                    )}
                </View>
                <Text style={styles.timeText}>
                    Active until: {new Date(item.valid_to).toLocaleString()}
                </Text>
            </View>
        );
    };

    const renderEarning = ({ item }: { item: DriverIncentiveEarning }) => (
        <View style={styles.earningCard}>
            <Text style={styles.earningText}>Earned bonus for Ride #{item.ride}</Text>
            <Text style={styles.earningAmount}>+₹{item.bonus_amount}</Text>
        </View>
    );

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#0000ff" />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Text style={styles.sectionHeader}>Active Incentives</Text>
            <FlatList
                data={incentives}
                renderItem={renderIncentive}
                keyExtractor={(item) => item.id.toString()}
                ListEmptyComponent={<Text style={styles.emptyText}>No active incentives in your city.</Text>}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
                style={styles.list}
            />

            <Text style={styles.sectionHeader}>Recent Earnings</Text>
            <FlatList
                data={earnings}
                renderItem={renderEarning}
                keyExtractor={(item) => item.id.toString()}
                ListEmptyComponent={<Text style={styles.emptyText}>No recent incentive earnings.</Text>}
                style={styles.list}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#f5f5f5",
        padding: 15,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
    },
    sectionHeader: {
        fontSize: 20,
        fontWeight: "bold",
        marginVertical: 10,
        color: "#333",
    },
    list: {
        marginBottom: 10,
    },
    card: {
        backgroundColor: "#fff",
        padding: 15,
        borderRadius: 10,
        marginBottom: 10,
        elevation: 2,
    },
    cardHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 5,
    },
    cardTitle: {
        fontSize: 16,
        fontWeight: "bold",
    },
    bonusBadge: {
        backgroundColor: "#E8F5E9",
        color: "#2E7D32",
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 5,
        fontWeight: "bold",
        fontSize: 14,
    },
    description: {
        fontSize: 14,
        color: "#666",
        marginBottom: 5,
    },
    detailsRow: {
        flexDirection: "row",
        marginBottom: 5,
    },
    detailText: {
        fontSize: 14,
        color: "#444",
        marginRight: 10,
    },
    timeText: {
        fontSize: 12,
        color: "#999",
        fontStyle: "italic",
    },
    earningCard: {
        backgroundColor: "#fff",
        padding: 15,
        borderRadius: 8,
        marginBottom: 5,
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
    },
    earningText: {
        fontSize: 14,
        color: "#333",
    },
    earningAmount: {
        fontSize: 16,
        fontWeight: "bold",
        color: "#2E7D32",
    },
    emptyText: {
        textAlign: "center",
        color: "#999",
        marginVertical: 10,
    },
});
