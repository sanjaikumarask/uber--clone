import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Alert, FlatList, ActivityIndicator } from "react-native";
import { api } from "../services/api";

export default function WalletScreen({ navigation }: any) {
    const [balance, setBalance] = useState<string>("0.00");
    const [transactions, setTransactions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchWalletData();
        fetchTransactions();
    }, []);

    async function fetchWalletData() {
        try {
            setLoading(true);
            const res = await api.get("payments/wallet/");
            setBalance(res.data.available_balance || res.data.total_balance || "0.00");
        } catch (err: any) {
            console.error("Failed to fetch wallet", err);
            if (err.response?.status !== 401) {
                Alert.alert("Error", "Could not load wallet details");
            }
        } finally {
            setLoading(false);
        }
    }

    async function fetchTransactions() {
        try {
            const res = await api.get("payments/transactions/");
            setTransactions(res.data || []);
        } catch (err) {
            console.error("Failed to fetch transactions", err);
        }
    }

    async function handleWithdraw() {
        try {
            const amount = parseFloat(balance);
            if (amount < 500) {
                Alert.alert("Minimum Withdrawal", "You need at least ₹500 to withdraw.");
                return;
            }

            Alert.alert(
                "Confirm Withdrawal",
                `Withdraw ₹${amount}?`,
                [
                    { text: "Cancel", style: "cancel" },
                    {
                        text: "Confirm",
                        onPress: async () => {
                            try {
                                await api.post(`payments/payout/instant/`, {
                                    amount: amount
                                });
                                Alert.alert("Success", "Withdrawal initiated!");
                                fetchWalletData();
                                fetchTransactions();
                            } catch (err: any) {
                                Alert.alert("Error", err.response?.data?.error || "Withdrawal failed");
                            }
                        }
                    }
                ]
            );
        } catch (err) {
            console.error("Withdraw error", err);
        }
    }

    const renderTransactionItem = ({ item }: { item: any }) => {
        const isCredit = item.type === "CREDIT";
        return (
            <View style={styles.transactionItem}>
                <View style={styles.transactionLeft}>
                    <View style={[styles.typeBadge, { backgroundColor: isCredit ? "#E8F5E9" : "#FFEBEE" }]}>
                        <Text style={[styles.typeText, { color: isCredit ? "#2E7D32" : "#C62828" }]}>
                            {isCredit ? "↑" : "↓"}
                        </Text>
                    </View>
                    <View>
                        <Text style={styles.reasonText}>{item.reason?.replace("_", " ")}</Text>
                        <Text style={styles.dateText}>{new Date(item.created_at).toLocaleDateString()}</Text>
                    </View>
                </View>
                <Text style={[styles.amountText, { color: isCredit ? "#2E7D32" : "#000" }]}>
                    {isCredit ? "+" : "-"}₹{parseFloat(item.amount).toFixed(2)}
                </Text>
            </View>
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
                <Text style={styles.title}>My Wallet</Text>
                <View style={{ width: 40 }} />
            </View>

            <View style={styles.balanceCard}>
                <Text style={styles.balanceLabel}>Current Balance</Text>
                <Text style={styles.balanceValue}>₹{balance}</Text>

                <TouchableOpacity style={styles.withdrawButton} onPress={handleWithdraw}>
                    <Text style={styles.withdrawText}>Withdraw Now</Text>
                </TouchableOpacity>
                <Text style={styles.noteText}>Min. withdrawal ₹500</Text>
            </View>

            <Text style={styles.sectionTitle}>Recent Transactions</Text>
            <FlatList
                data={transactions}
                keyExtractor={(item) => item.id.toString()}
                renderItem={renderTransactionItem}
                contentContainerStyle={{ paddingBottom: 40 }}
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyText}>No recent transactions</Text>
                    </View>
                }
            />
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
    center: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 30,
    },
    backText: {
        fontSize: 16,
        color: "#007AFF",
    },
    title: {
        fontSize: 20,
        fontWeight: "bold",
    },
    balanceCard: {
        backgroundColor: "#000",
        borderRadius: 15,
        padding: 25,
        alignItems: "center",
        marginBottom: 30,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 5,
        elevation: 6,
    },
    balanceLabel: {
        color: "#aaa",
        fontSize: 14,
        marginBottom: 5,
        textTransform: "uppercase",
    },
    balanceValue: {
        color: "#fff",
        fontSize: 36,
        fontWeight: "bold",
        marginBottom: 20,
    },
    withdrawButton: {
        backgroundColor: "#fff",
        paddingVertical: 12,
        paddingHorizontal: 30,
        borderRadius: 25,
        width: "100%",
        alignItems: "center",
    },
    withdrawText: {
        color: "#000",
        fontSize: 16,
        fontWeight: "bold",
    },
    noteText: {
        color: "#666",
        marginTop: 10,
        fontSize: 12,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: "bold",
        marginBottom: 15,
    },
    emptyState: {
        padding: 40,
        alignItems: "center",
    },
    emptyText: {
        color: "#999",
    },
    transactionItem: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        backgroundColor: "#fff",
        padding: 15,
        borderRadius: 12,
        marginBottom: 10,
    },
    transactionLeft: {
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
    },
    typeBadge: {
        width: 40,
        height: 40,
        borderRadius: 20,
        justifyContent: "center",
        alignItems: "center",
    },
    typeText: {
        fontSize: 20,
        fontWeight: "bold",
    },
    reasonText: {
        fontSize: 14,
        fontWeight: "600",
        color: "#333",
        textTransform: "capitalize",
    },
    dateText: {
        fontSize: 12,
        color: "#999",
        marginTop: 2,
    },
    amountText: {
        fontSize: 16,
        fontWeight: "bold",
    },
});
