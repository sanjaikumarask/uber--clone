import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator, StatusBar, ScrollView, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import RazorpayCheckout from 'react-native-razorpay';
import { api } from '../../services/api';
import { Storage } from '../../services/storage';
import Colors from '../../constants/Colors';

const { width } = Dimensions.get('window');

export default function SummaryScreen() {
    const router = useRouter();
    const params = useLocalSearchParams<{ rideId: string }>();

    const [loading, setLoading] = useState(true);
    const [ride, setRide] = useState<any>(null);
    const [breakdown, setBreakdown] = useState<any>(null);
    const [paymentStatus, setPaymentStatus] = useState<"pending" | "success">("pending");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchRideAndBreakdown();
    }, []);

    const fetchRideAndBreakdown = async () => {
        try {
            const [rideRes, breakdownRes] = await Promise.all([
                api.get(`/rides/${params.rideId}/`),
                api.get(`/rides/${params.rideId}/fare-breakdown/`).catch(() => null)
            ]);

            setRide(rideRes.data);
            if (breakdownRes) setBreakdown(breakdownRes.data);

            if (rideRes.data.payment_status === "CAPTURED") {
                setPaymentStatus("success");
            }
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch ride data", err);
        }
    };

    const handlePayment = async () => {
        setSubmitting(true);
        try {
            // Guard: already paid?
            const currentRide = await api.get(`/rides/${params.rideId}/`);
            if (currentRide.data.payment_status === 'CAPTURED') {
                router.replace({
                    pathname: '/screens/payment-success',
                    params: { rideId: params.rideId },
                });
                return;
            }

            // Step 1: Create order on backend
            const orderRes = await api.post(`/payments/native-order/${params.rideId}/`);

            if (orderRes.data.error === 'already_paid') {
                router.replace({
                    pathname: '/screens/payment-success',
                    params: { rideId: params.rideId },
                });
                return;
            }

            const { order_id, amount, currency, key, name, description, prefill } = orderRes.data;

            // Step 2: Open native Razorpay SDK
            const options = {
                description: description || `Trip #${params.rideId}`,
                image: 'https://i.imgur.com/3g7nmJC.png',
                currency: currency || 'INR',
                key: key,
                amount: amount, // MUST be integer/number in paise
                order_id: order_id,
                name: name || 'Tripzo',
                prefill: {
                    name: prefill?.name || '',
                    email: prefill?.email || '',
                    contact: prefill?.contact || ''
                },
                theme: { color: '#276EF1' },
            };

            console.log("Opening Razorpay with:", options);

            // Step 3: Handle result
            RazorpayCheckout.open(options)
                .then(async (data: any) => {
                    // Payment SUCCESS — data has razorpay_payment_id, razorpay_order_id, razorpay_signature
                    try {
                        await api.post('/payments/verify/', {
                            razorpay_payment_id: data.razorpay_payment_id,
                            razorpay_order_id: data.razorpay_order_id,
                            razorpay_signature: data.razorpay_signature,
                        });
                        router.replace({
                            pathname: '/screens/payment-success',
                            params: { rideId: params.rideId },
                        });
                    } catch (verifyErr: any) {
                        Alert.alert(
                            "Verification Failed",
                            "Payment was received but verification failed. Our team will resolve this within 24 hours.",
                        );
                    } finally {
                        setSubmitting(false);
                    }
                })
                .catch((error: any) => {
                    const code = error?.code;
                    const desc = error?.description || '';

                    if (code === 0 || desc.toLowerCase().includes('cancel')) {
                        // User dismissed — silent, just re-enable button
                        // No alert needed, they can tap Pay again
                    } else if (code === 2) {
                        Alert.alert(
                            "Payment Failed",
                            "Your payment was declined. Please try a different payment method.",
                            [{ text: "Try Again", onPress: () => handlePayment() }]
                        );
                    } else {
                        Alert.alert(
                            "Payment Error",
                            desc || "Something went wrong. Please try again.",
                            [{ text: "OK" }]
                        );
                    }
                    setSubmitting(false);
                });

            // NOTE: do NOT put setSubmitting(false) here —
            // it's handled inside .then() and .catch() above
            // because RazorpayCheckout.open() is async callback-based

        } catch (err: any) {
            const msg = err.response?.data?.error || "Failed to initiate payment.";
            Alert.alert("Payment Error", msg);
            setSubmitting(false);
        }
    };

    const handleSimulatePayment = async () => {
        setSubmitting(true);
        try {
            await api.post(`/payments/simulate/${params.rideId}/`);
            // Navigate to success celebration
            router.replace({
                pathname: '/screens/payment-success',
                params: { rideId: params.rideId },
            });
        } catch (error: any) {
            Alert.alert("Payment Failed", error.response?.data?.error || "Simulation failed.");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <View style={styles.center}>
                <StatusBar barStyle="dark-content" backgroundColor="#fff" />
                <ActivityIndicator size="large" color={Colors.primary} />
            </View>
        );
    }

    return (
        <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 60 }} showsVerticalScrollIndicator={false}>
            <StatusBar barStyle="dark-content" backgroundColor="#fff" />

            <View style={styles.header}>
                <Text style={styles.title}>Trip Summary<Text style={styles.dot}>.</Text></Text>
                <Text style={styles.subtitle}>Ride completed successfully</Text>
            </View>

            <View style={styles.summaryCard}>
                <View style={[styles.row, { alignItems: 'flex-end' }]}>
                    <View>
                        <Text style={styles.label}>Total Fare</Text>
                        <Text style={styles.price}>₹{breakdown?.total_with_tip || ride?.final_fare || ride?.fare}</Text>
                    </View>
                    <View style={styles.statusBadge}>
                        <Text style={[styles.statusText, paymentStatus === "success" && { color: "#22C55E" }]}>
                            {paymentStatus === "success" ? "PAID" : "UNPAID"}
                        </Text>
                    </View>
                </View>

                {breakdown && (
                    <View style={styles.breakdownContainer}>
                        <View style={styles.breakdownRow}>
                            <Text style={styles.breakdownLabel}>Base Fare</Text>
                            <Text style={styles.breakdownValue}>₹{breakdown.base_fare}</Text>
                        </View>
                        <View style={styles.breakdownRow}>
                            <Text style={styles.breakdownLabel}>Distance ({breakdown.actual_distance_km} km)</Text>
                            <Text style={styles.breakdownValue}>+ ₹{breakdown.distance_charge}</Text>
                        </View>
                        {parseFloat(breakdown.waiting_charge) > 0 && (
                            <View style={styles.breakdownRow}>
                                <Text style={styles.breakdownLabel}>Waiting Charge</Text>
                                <Text style={styles.breakdownValue}>+ ₹{breakdown.waiting_charge}</Text>
                            </View>
                        )}
                        {parseFloat(breakdown.surge_multiplier) > 1 && (
                            <View style={styles.breakdownRow}>
                                <Text style={[styles.breakdownLabel, { color: Colors.primary }]}>Surge ({breakdown.surge_multiplier}x)</Text>
                                <Text style={[styles.breakdownValue, { color: Colors.primary }]}>Included</Text>
                            </View>
                        )}
                        {parseFloat(breakdown.discount_amount) > 0 && (
                            <View style={styles.breakdownRow}>
                                <Text style={[styles.breakdownLabel, { color: '#22C55E' }]}>Offered Discount</Text>
                                <Text style={[styles.breakdownValue, { color: '#22C55E' }]}>- ₹{breakdown.discount_amount}</Text>
                            </View>
                        )}
                    </View>
                )}

                <View style={styles.divider} />

                <View style={styles.routeRow}>
                    <View style={styles.routeDots}>
                        <View style={styles.dotWhite} />
                        <View style={styles.routeLine} />
                        <View style={styles.dotBlue} />
                    </View>
                    <View style={styles.routeAddresses}>
                        <Text style={styles.addressText} numberOfLines={1}>{ride?.pickup_address}</Text>
                        <Text style={styles.addressText} numberOfLines={1}>{ride?.drop_address}</Text>
                    </View>
                </View>

                {ride?.driver && (
                    <>
                        <View style={styles.divider} />
                        <View style={styles.driverRow}>
                            <View style={styles.driverAvatar}>
                                <Text style={styles.avatarEmoji}>👨‍✈️</Text>
                            </View>
                            <View>
                                <Text style={styles.driverName}>
                                    {ride.driver.user.first_name || ride.driver.user.username}
                                </Text>
                                <Text style={styles.vehicleName}>{ride.driver.vehicle_model} · {ride.driver.vehicle_number}</Text>
                            </View>
                        </View>
                    </>
                )}
            </View>

            {paymentStatus === "pending" ? (
                <View style={styles.paymentActions}>
                    <TouchableOpacity
                        style={[styles.payBtn, submitting && styles.disabled]}
                        onPress={handlePayment}
                        disabled={submitting}
                    >
                        <Ionicons name="card-outline" size={24} color={Colors.white} style={{marginRight: 10}} />
                        {submitting ? <ActivityIndicator color={Colors.white} /> : (
                            <Text style={styles.payText}>Pay ₹{ride?.final_fare || ride?.fare} Online</Text>
                        )}
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={[styles.simBtn, submitting && styles.disabled]}
                        onPress={handleSimulatePayment}
                        disabled={submitting}
                    >
                        <Text style={styles.simText}>Pay via Cash / Wallet</Text>
                    </TouchableOpacity>
                </View>
            ) : (
                <View style={styles.paymentActions}>
                    <TouchableOpacity
                        style={styles.payBtn}
                        onPress={() => router.replace({ pathname: '/screens/payment-success', params: { rideId: params.rideId } })}
                    >
                        <Text style={styles.payText}>Continue to Rating</Text>
                    </TouchableOpacity>
                </View>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: Colors.white, padding: 24 },
    center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: Colors.white },
    header: { marginTop: 40, marginBottom: 32 },
    title: { fontSize: 34, fontWeight: "900", color: Colors.textDark, letterSpacing: -1 },
    dot: { color: Colors.primary },
    subtitle: { fontSize: 15, color: Colors.textMuted, fontWeight: "500", marginTop: 4 },
    summaryCard: { backgroundColor: Colors.primaryBg, borderRadius: 24, padding: 24, marginBottom: 32, borderWidth: 1.5, borderColor: Colors.primaryBorder },
    row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    label: { fontSize: 11, fontWeight: "700", color: Colors.textMid, letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 4 },
    price: { fontSize: 32, fontWeight: "900", color: Colors.textDark },
    statusBadge: { backgroundColor: 'rgba(245, 166, 35, 0.15)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10 },
    statusText: { fontSize: 12, fontWeight: "900", color: Colors.primary, letterSpacing: 0.5 },
    divider: { height: 1, backgroundColor: '#E0E0E0', marginVertical: 20 },
    routeRow: { flexDirection: "row", alignItems: "center", gap: 16 },
    routeDots: { alignItems: "center", gap: 4 },
    dotWhite: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.primary },
    routeLine: { width: 1, height: 20, backgroundColor: '#D4D4D4' },
    dotBlue: { width: 8, height: 8, borderRadius: 2, backgroundColor: Colors.textDark },
    routeAddresses: { flex: 1, gap: 12 },
    addressText: { fontSize: 14, color: Colors.textMid, fontWeight: "500" },
    driverRow: { flexDirection: "row", alignItems: "center", gap: 14 },
    driverAvatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#FFF9E6', alignItems: "center", justifyContent: "center" },
    avatarEmoji: { fontSize: 24 },
    driverName: { fontSize: 16, fontWeight: "800", color: Colors.textDark },
    vehicleName: { fontSize: 13, color: Colors.textSub, fontWeight: "500" },
    paymentActions: { gap: 16 },
    payBtn: { backgroundColor: Colors.primary, paddingVertical: 18, borderRadius: 16, alignItems: "center", flexDirection: 'row', justifyContent: 'center', shadowColor: Colors.shadow, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 10, elevation: 5 },
    payText: { color: Colors.white, fontWeight: "900", fontSize: 17 },
    simBtn: { alignItems: "center", paddingVertical: 12 },
    simText: { color: Colors.textSub, fontWeight: "600", fontSize: 15 },
    disabled: { opacity: 0.7 },
    breakdownContainer: { marginTop: 20, gap: 8 },
    breakdownRow: { flexDirection: 'row', justifyContent: 'space-between' },
    breakdownLabel: { fontSize: 13, color: Colors.textSub, fontWeight: '500' },
    breakdownValue: { fontSize: 13, color: Colors.textMid, fontWeight: '600' },
});
