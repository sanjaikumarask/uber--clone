import React, { useEffect, useState } from "react";
import {
    View, Text, StyleSheet, FlatList, RefreshControl,
    ActivityIndicator, Alert, TouchableOpacity, StatusBar, Platform
} from "react-native";
import { Offer, getActiveOffers } from "../services/offerService";

export default function OffersScreen({ navigation }: any) {
    const [offers, setOffers] = useState<Offer[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = async () => {
        try {
            const data = await getActiveOffers("Chennai");
            setOffers(data);
        } catch (error) {
            console.error("Failed to fetch offers", error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => { fetchData(); }, []);

    const onRefresh = () => { setRefreshing(true); fetchData(); };

    const renderOffer = ({ item }: { item: Offer }) => {
        const isFlat = item.discount_type === "FLAT";
        return (
            <View style={styles.card}>
                {/* Top badge */}
                <View style={styles.cardTop}>
                    <View style={styles.tagRow}>
                        <View style={[styles.discountBadge, { backgroundColor: isFlat ? "rgba(39,110,241,0.15)" : "rgba(245,158,11,0.15)" }]}>
                            <Text style={[styles.discountText, { color: isFlat ? "#276EF1" : "#f59e0b" }]}>
                                {isFlat ? `₹${item.value}` : `${item.value}%`} OFF
                            </Text>
                        </View>
                    </View>
                    <Text style={styles.cardTitle}>{item.title}</Text>
                    <Text style={styles.description}>{item.description || `Use code ${item.code}`}</Text>
                </View>

                <View style={styles.divider} />

                <View style={styles.cardBottom}>
                    <Text style={styles.expiryText}>
                        🕐 Expires {new Date(item.valid_to).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                    </Text>
                    <TouchableOpacity
                        style={styles.applyBtn}
                        onPress={() => Alert.alert("Offer Applied!", `"${item.title}" will be applied at checkout.`)}
                        activeOpacity={0.8}
                    >
                        <Text style={styles.applyText}>APPLY</Text>
                    </TouchableOpacity>
                </View>
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
                <View>
                    <Text style={styles.headerTitle}>Offers<Text style={styles.headerAccent}>.</Text></Text>
                    <Text style={styles.headerSub}>Exclusive deals for you</Text>
                </View>
            </View>

            {loading ? (
                <View style={styles.center}>
                    <ActivityIndicator size="large" color="#276EF1" />
                </View>
            ) : (
                <FlatList
                    data={offers}
                    renderItem={renderOffer}
                    keyExtractor={(item) => item.id.toString()}
                    contentContainerStyle={styles.list}
                    showsVerticalScrollIndicator={false}
                    refreshControl={
                        <RefreshControl
                            refreshing={refreshing}
                            onRefresh={onRefresh}
                            tintColor="#276EF1"
                            colors={["#276EF1"]}
                        />
                    }
                    ListEmptyComponent={
                        <View style={styles.empty}>
                            <Text style={styles.emptyEmoji}>🎁</Text>
                            <Text style={styles.emptyTitle}>No offers right now</Text>
                            <Text style={styles.emptyText}>Check back soon for exclusive deals.</Text>
                        </View>
                    }
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
    center: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
    },
    header: {
        flexDirection: "row",
        alignItems: "center",
        paddingTop: Platform.OS === "ios" ? 60 : 48,
        paddingBottom: 20,
        paddingHorizontal: 20,
        gap: 16,
        borderBottomWidth: 1,
        borderBottomColor: "rgba(255,255,255,0.06)",
    },
    backBtn: {
        width: 40, height: 40, borderRadius: 20,
        backgroundColor: "rgba(255,255,255,0.07)",
        borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
        alignItems: "center", justifyContent: "center",
    },
    backArrow: { fontSize: 18, fontWeight: "700", color: "#FFFFFF" },
    headerTitle: { fontSize: 26, fontWeight: "900", color: "#FFFFFF", letterSpacing: -0.5 },
    headerAccent: { color: "#276EF1" },
    headerSub: { fontSize: 12, color: "#555", marginTop: 2, fontWeight: "500" },

    list: { padding: 20, gap: 14 },

    card: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        overflow: "hidden",
    },
    cardTop: { padding: 20 },
    tagRow: { marginBottom: 10 },
    discountBadge: {
        alignSelf: "flex-start",
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 8,
    },
    discountText: { fontSize: 12, fontWeight: "900", letterSpacing: 0.5 },
    cardTitle: { fontSize: 18, fontWeight: "800", color: "#FFFFFF", marginBottom: 6 },
    description: { fontSize: 13, color: "#666", lineHeight: 19 },

    divider: { height: 1, backgroundColor: "rgba(255,255,255,0.06)" },

    cardBottom: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        paddingHorizontal: 20,
        paddingVertical: 14,
    },
    expiryText: { fontSize: 12, color: "#555", fontWeight: "500" },
    applyBtn: {
        backgroundColor: "#276EF1",
        paddingHorizontal: 18,
        paddingVertical: 8,
        borderRadius: 20,
    },
    applyText: { color: "#fff", fontWeight: "900", fontSize: 12, letterSpacing: 0.8 },

    empty: { alignItems: "center", paddingTop: 80, gap: 10 },
    emptyEmoji: { fontSize: 48 },
    emptyTitle: { fontSize: 20, fontWeight: "800", color: "#FFFFFF" },
    emptyText: { fontSize: 14, color: "#555" },
});
