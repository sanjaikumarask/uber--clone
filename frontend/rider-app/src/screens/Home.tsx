import React, { useEffect, useRef } from "react";
import {
    View, Text, StyleSheet, TouchableOpacity, StatusBar,
    Platform, Animated
} from "react-native";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";

export default function HomeScreen({ navigation }: any) {
    const { logout } = useAuth();
    const fadeAnim = useRef(new Animated.Value(0)).current;
    const slideAnim = useRef(new Animated.Value(20)).current;

    // Redirect to active ride if one exists
    useEffect(() => {
        const checkActive = async () => {
            try {
                const res = await api.get("rides/active/");
                if (res.data?.id) {
                    const status = res.data.status;
                    if (status === "SEARCHING" || status === "OFFERED") {
                        navigation.replace("RideSearching", {
                            rideId: res.data.id,
                            vehicleType: res.data.vehicle_type
                        });
                    } else {
                        navigation.replace("RideTracking", { rideId: res.data.id });
                    }
                }
            } catch { /* no active ride */ }
        };
        checkActive();
    }, []);

    useEffect(() => {
        Animated.parallel([
            Animated.timing(fadeAnim, {
                toValue: 1,
                duration: 800,
                useNativeDriver: true,
            }),
            Animated.timing(slideAnim, {
                toValue: 0,
                duration: 800,
                useNativeDriver: true,
            }),
        ]).start();
    }, []);

    return (
        <View style={styles.root}>
            <StatusBar barStyle="light-content" backgroundColor="#000" />

            {/* Central Card Container */}
            <View style={styles.centerContainer}>
                <Animated.View style={[styles.mainCard, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>

                    {/* Hero Text */}
                    <View style={styles.header}>
                        <Text style={styles.title}>Where to?</Text>
                        <Text style={styles.subtitle}>Get a reliable ride in minutes.</Text>
                    </View>

                    {/* Request Ride CTA */}
                    <TouchableOpacity
                        style={styles.requestBtn}
                        onPress={() => navigation.navigate("DestinationSearch")}
                        activeOpacity={0.8}
                    >
                        <Text style={styles.requestBtnText}>Request a Ride</Text>
                    </TouchableOpacity>

                    {/* Quick Links Row */}
                    <View style={styles.linksRow}>
                        <TouchableOpacity
                            style={styles.linkBtn}
                            onPress={() => navigation.navigate("Offers")}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.linkText}><Text style={styles.emoji}>🎁</Text> Offers</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.linkBtn}
                            onPress={() => navigation.navigate("Support")}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.linkText}><Text style={styles.emoji}>🎧</Text> Support</Text>
                        </TouchableOpacity>
                    </View>

                </Animated.View>
            </View>

            {/* Subtle Logout Option at bottom */}
            <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
                <Text style={styles.logoutText}>Sign Out</Text>
            </TouchableOpacity>
        </View>
    );
}

const styles = StyleSheet.create({
    root: {
        flex: 1,
        backgroundColor: "#000000",
        justifyContent: "center",
        alignItems: "center",
    },
    centerContainer: {
        width: "90%",
        maxWidth: 400,
    },
    mainCard: {
        backgroundColor: "#0A0A0A",
        borderRadius: 32,
        padding: 40,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.05)",
        alignItems: "center",
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 20 },
        shadowOpacity: 0.5,
        shadowRadius: 40,
        elevation: 10,
    },
    header: {
        alignItems: "center",
        marginBottom: 40,
    },
    title: {
        fontSize: 42,
        fontWeight: "900",
        color: "#FFFFFF",
        letterSpacing: -1,
        marginBottom: 12,
    },
    subtitle: {
        fontSize: 16,
        color: "rgba(255,255,255,0.4)",
        fontWeight: "500",
        textAlign: "center",
    },
    requestBtn: {
        width: "100%",
        backgroundColor: "#000000",
        borderRadius: 18,
        paddingVertical: 22,
        alignItems: "center",
        justifyContent: "center",
        marginBottom: 16,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.4,
        shadowRadius: 15,
        elevation: 8,
    },
    requestBtnText: {
        color: "#FFFFFF",
        fontSize: 20,
        fontWeight: "800",
        letterSpacing: -0.2,
    },
    linksRow: {
        flexDirection: "row",
        width: "100%",
        gap: 12,
    },
    linkBtn: {
        flex: 1,
        backgroundColor: "rgba(255,255,255,0.03)",
        borderRadius: 16,
        paddingVertical: 18,
        alignItems: "center",
        justifyContent: "center",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.06)",
    },
    linkText: {
        color: "#FFFFFF",
        fontSize: 15,
        fontWeight: "700",
    },
    emoji: {
        fontSize: 16,
    },
    logoutBtn: {
        position: "absolute",
        bottom: Platform.OS === "ios" ? 60 : 40,
        backgroundColor: "rgba(255,255,255,0.05)",
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
    },
    logoutText: {
        color: "rgba(255,255,255,0.5)",
        fontSize: 14,
        fontWeight: "600",
        letterSpacing: 0.5,
    },
});
