import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity, TextInput, Alert, ActivityIndicator, StatusBar, ScrollView, NativeModules } from "react-native";
import { api } from "../services/api";
import RazorpayCheckout from "react-native-razorpay";

export default function RideCompletionScreen({ navigation, route }: any) {
    const { rideId } = route.params;
    const [ride, setRide] = useState<any>(null);
    const [breakdown, setBreakdown] = useState<any>(null);
    const [rating, setRating] = useState(0);
    const [comment, setComment] = useState("");
    const [tipAmount, setTipAmount] = useState<string>("");
    const [tipSubmitting, setTipSubmitting] = useState(false);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [paymentStatus, setPaymentStatus] = useState<"pending" | "success">("pending");

    useEffect(() => {
        fetchRideAndBreakdown();
    }, []);

    const fetchRideAndBreakdown = async () => {
        try {
            const [rideRes, breakdownRes] = await Promise.all([
                api.get(`/rides/${rideId}/`),
                api.get(`/rides/${rideId}/fare-breakdown/`).catch(() => null)
            ]);

            setRide(rideRes.data);
            if (breakdownRes) setBreakdown(breakdownRes.data);

            if (rideRes.data.payment_status === "CAPTURED" || rideRes.data.payment_status === "SUCCESS") {
                setPaymentStatus("success");
            }
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch ride data", err);
            Alert.alert("Error", "Could not load ride summary.");
        }
    };

    const handlePayment = async () => {
        setSubmitting(true);

        const isNativeReady = !!(NativeModules.RNRazorpayCheckout || NativeModules.RazorpayCheckout || NativeModules.Razorpay);

        if (!isNativeReady) {
            setSubmitting(false);
            Alert.alert(
                "Native Module Missing",
                "Razorpay's native component is not found. \n\nIMPORTANT: Use the Development Build, NOT Expo Go.",
                [{ text: "OK" }]
            );
            return;
        }

        try {
            const orderRes = await api.post(`/payments/create/${rideId}/`);
            const { order_id, amount, key, currency } = orderRes.data;

            const options = {
                description: `Uber Ride #${rideId}`,
                image: "https://i.imgur.com/3g7Y69t.png",
                currency: currency,
                key: key,
                amount: amount,
                name: "Uber",
                order_id: order_id,
                prefill: {
                    email: ride?.rider?.user?.email || "",
                    contact: ride?.rider?.user?.phone || "",
                    name: ride?.rider?.user?.first_name || "",
                },
                theme: { color: "#000000" }
            };

            RazorpayCheckout.open(options).then(async (data: any) => {
                try {
                    await api.post(`/payments/verify/`, {
                        razorpay_order_id: data.razorpay_order_id,
                        razorpay_payment_id: data.razorpay_payment_id,
                        razorpay_signature: data.razorpay_signature,
                    });
                    setPaymentStatus("success");
                    Alert.alert("Success", "Payment verified successfully!");
                } catch (err) {
                    Alert.alert("Error", "Payment verification failed.");
                }
            }).catch((error: any) => {
                Alert.alert("Payment Cancelled", error.description || "Checkout closed.");
            });

        } catch (err: any) {
            Alert.alert("Payment Error", "Failed to initiate payment.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleAddTip = async (amount?: string) => {
        const finalAmount = amount || tipAmount;
        if (!finalAmount || parseFloat(finalAmount) <= 0) return;

        setTipSubmitting(true);
        try {
            await api.post(`/rides/${rideId}/tip/`, {
                tip_amount: finalAmount
            });
            Alert.alert("Thank You!", `₹${finalAmount} tip has been sent to the driver.`);
            // Refresh breakdown to show tip
            const res = await api.get(`/rides/${rideId}/fare-breakdown/`);
            setBreakdown(res.data);
            setTipAmount("");
        } catch (err: any) {
            Alert.alert("Error", err.response?.data?.error || "Failed to add tip.");
        } finally {
            setTipSubmitting(false);
        }
    };

    const handleSubmitRating = async () => {
        if (rating === 0) {
            Alert.alert("Rating Required", "Please select a star rating.");
            return;
        }
        setSubmitting(true);
        try {
            await api.post(`/rides/${rideId}/feedback/`, {
                rating: rating,
                comment: comment
            });
            Alert.alert("Success", "Thank you for your feedback!");
            navigation.replace("Home");
        } catch (err: any) {
            Alert.alert("Error", "Failed to submit rating.");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <View style={styles.center}>
                <StatusBar barStyle="light-content" />
                <ActivityIndicator size="large" color="#276EF1" />
            </View>
        );
    }

    return (
        <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 60 }}>
            <StatusBar barStyle="light-content" />

            <View style={styles.header}>
                <Text style={styles.title}>Trip Summary<Text style={styles.dot}>.</Text></Text>
                <Text style={styles.subtitle}>Ride completed successfully</Text>
            </View>

            {/* Summary Card */}
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
                                <Text style={[styles.breakdownLabel, { color: '#F59E0B' }]}>Surge ({breakdown.surge_multiplier}x)</Text>
                                <Text style={[styles.breakdownValue, { color: '#F59E0B' }]}>Included</Text>
                            </View>
                        )}
                        {parseFloat(breakdown.discount_amount) > 0 && (
                            <View style={styles.breakdownRow}>
                                <Text style={[styles.breakdownLabel, { color: '#22C55E' }]}>Offered Discount</Text>
                                <Text style={[styles.breakdownValue, { color: '#22C55E' }]}>- ₹{breakdown.discount_amount}</Text>
                            </View>
                        )}
                        {parseFloat(breakdown.tip_amount) > 0 && (
                            <View style={styles.breakdownRow}>
                                <Text style={styles.breakdownLabel}>Tip</Text>
                                <Text style={styles.breakdownValue}>+ ₹{breakdown.tip_amount}</Text>
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
                        activeOpacity={0.8}
                    >
                        {submitting ? <ActivityIndicator color="#fff" /> : (
                            <Text style={styles.payText}>Pay ₹{ride?.final_fare || ride?.fare} Now</Text>
                        )}
                    </TouchableOpacity>
                </View>
            ) : (
                <View style={styles.postPaymentSection}>
                    {/* Tip Section */}
                    {parseFloat(breakdown?.tip_amount || "0") === 0 && (
                        <View style={styles.tipCard}>
                            <Text style={styles.tipTitle}>Add a tip for {ride?.driver?.user?.first_name || 'the driver'}</Text>
                            <Text style={styles.tipSub}>100% of your tip goes to the driver</Text>

                            <View style={styles.tipPresets}>
                                {['10', '20', '50'].map(amt => (
                                    <TouchableOpacity
                                        key={amt}
                                        style={styles.tipPresetBtn}
                                        onPress={() => handleAddTip(amt)}
                                        disabled={tipSubmitting}
                                    >
                                        <Text style={styles.tipPresetText}>+ ₹{amt}</Text>
                                    </TouchableOpacity>
                                ))}
                            </View>

                            <View style={styles.customTipRow}>
                                <TextInput
                                    style={styles.tipInput}
                                    placeholder="Other amount"
                                    placeholderTextColor="#555"
                                    keyboardType="numeric"
                                    value={tipAmount}
                                    onChangeText={setTipAmount}
                                />
                                <TouchableOpacity
                                    style={[styles.tipSubmitBtn, (!tipAmount || tipSubmitting) && { opacity: 0.5 }]}
                                    onPress={() => handleAddTip()}
                                    disabled={!tipAmount || tipSubmitting}
                                >
                                    {tipSubmitting ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.tipSubmitText}>Tip</Text>}
                                </TouchableOpacity>
                            </View>
                        </View>
                    )}

                    <View style={styles.ratingSection}>
                        <Text style={styles.ratingTitle}>How was your trip?</Text>
                        <Text style={styles.ratingSub}>Rate your experience with {ride?.driver?.user?.first_name || "your driver"}</Text>

                        <View style={styles.stars}>
                            {[1, 2, 3, 4, 5].map((s) => (
                                <TouchableOpacity key={s} onPress={() => setRating(s)} activeOpacity={0.7}>
                                    <Text style={[styles.star, rating >= s && styles.starSelected]}>★</Text>
                                </TouchableOpacity>
                            ))}
                        </View>

                        <TextInput
                            style={styles.input}
                            placeholder="Share your feedback..."
                            placeholderTextColor="#444"
                            value={comment}
                            onChangeText={setComment}
                            multiline
                        />

                        <TouchableOpacity
                            style={[styles.submitBtn, submitting && styles.disabled]}
                            onPress={handleSubmitRating}
                            disabled={submitting}
                            activeOpacity={0.8}
                        >
                            {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitText}>Submit & Back Home</Text>}
                        </TouchableOpacity>
                    </View>
                </View>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#000",
        padding: 24,
    },
    center: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#000",
    },
    header: {
        marginTop: 40,
        marginBottom: 32,
    },
    title: {
        fontSize: 34,
        fontWeight: "900",
        color: "#FFFFFF",
        letterSpacing: -1,
    },
    dot: {
        color: "#276EF1",
    },
    subtitle: {
        fontSize: 15,
        color: "#666",
        fontWeight: "500",
        marginTop: 4,
    },
    summaryCard: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 24,
        padding: 24,
        marginBottom: 32,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
    },
    row: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
    },
    label: {
        fontSize: 11,
        fontWeight: "700",
        color: "#444",
        letterSpacing: 1.2,
        textTransform: "uppercase",
        marginBottom: 4,
    },
    price: {
        fontSize: 32,
        fontWeight: "900",
        color: "#FFFFFF",
    },
    statusBadge: {
        backgroundColor: "rgba(255,255,255,0.05)",
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 10,
    },
    statusText: {
        fontSize: 12,
        fontWeight: "900",
        color: "#F59E0B",
        letterSpacing: 0.5,
    },
    divider: {
        height: 1,
        backgroundColor: "rgba(255,255,255,0.06)",
        marginVertical: 20,
    },
    routeRow: {
        flexDirection: "row",
        alignItems: "center",
        gap: 16,
    },
    routeDots: {
        alignItems: "center",
        gap: 4,
    },
    dotWhite: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#fff" },
    routeLine: { width: 1, height: 20, backgroundColor: "rgba(255,255,255,0.2)" },
    dotBlue: { width: 8, height: 8, borderRadius: 2, backgroundColor: "#276EF1" },
    routeAddresses: {
        flex: 1,
        gap: 12,
    },
    addressText: {
        fontSize: 14,
        color: "#A6A6A6",
        fontWeight: "500",
    },
    driverRow: {
        flexDirection: "row",
        alignItems: "center",
        gap: 14,
    },
    driverAvatar: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: "rgba(255,255,255,0.05)",
        alignItems: "center",
        justifyContent: "center",
    },
    avatarEmoji: { fontSize: 24 },
    driverName: {
        fontSize: 16,
        fontWeight: "800",
        color: "#FFFFFF",
    },
    vehicleName: {
        fontSize: 13,
        color: "#555",
        fontWeight: "500",
    },
    paymentActions: {
        gap: 16,
    },
    payBtn: {
        backgroundColor: "#276EF1",
        paddingVertical: 18,
        borderRadius: 16,
        alignItems: "center",
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.3,
        shadowRadius: 16,
        elevation: 10,
    },
    payText: {
        color: "#FFFFFF",
        fontWeight: "900",
        fontSize: 17,
    },
    simBtn: {
        alignItems: "center",
        paddingVertical: 12,
    },
    simText: {
        color: "#444",
        fontWeight: "600",
        fontSize: 14,
    },
    ratingSection: {
        alignItems: "center",
    },
    ratingTitle: {
        fontSize: 24,
        fontWeight: "900",
        color: "#FFFFFF",
        textAlign: "center",
        marginBottom: 8,
    },
    ratingSub: {
        fontSize: 14,
        color: "#555",
        fontWeight: "500",
        textAlign: "center",
        marginBottom: 32,
    },
    stars: {
        flexDirection: "row",
        gap: 12,
        marginBottom: 32,
    },
    star: {
        fontSize: 48,
        color: "rgba(255,255,255,0.08)",
    },
    starSelected: {
        color: "#F59E0B",
    },
    input: {
        width: "100%",
        height: 120,
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 16,
        padding: 18,
        color: "#FFFFFF",
        fontSize: 15,
        fontWeight: "500",
        textAlignVertical: "top",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
        marginBottom: 24,
    },
    submitBtn: {
        backgroundColor: "#276EF1",
        paddingVertical: 18,
        width: "100%",
        borderRadius: 16,
        alignItems: "center",
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.3,
        shadowRadius: 16,
        elevation: 10,
    },
    submitText: {
        color: "#FFFFFF",
        fontWeight: "900",
        fontSize: 18,
    },
    disabled: {
        opacity: 0.7,
    },
    breakdownContainer: {
        marginTop: 20,
        gap: 8,
    },
    breakdownRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    breakdownLabel: {
        fontSize: 13,
        color: '#666',
        fontWeight: '500',
    },
    breakdownValue: {
        fontSize: 13,
        color: '#A6A6A6',
        fontWeight: '600',
    },
    postPaymentSection: {
        gap: 32,
    },
    tipCard: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: 20,
        padding: 20,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
    },
    tipTitle: {
        fontSize: 16,
        fontWeight: "800",
        color: "#FFFFFF",
        textAlign: "center",
        marginBottom: 4,
    },
    tipSub: {
        fontSize: 12,
        color: "#666",
        textAlign: "center",
        marginBottom: 20,
    },
    tipPresets: {
        flexDirection: 'row',
        justifyContent: 'center',
        gap: 12,
        marginBottom: 16,
    },
    tipPresetBtn: {
        backgroundColor: 'rgba(39, 110, 241, 0.1)',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: 'rgba(39, 110, 241, 0.2)',
    },
    tipPresetText: {
        color: '#276EF1',
        fontWeight: '800',
        fontSize: 14,
    },
    customTipRow: {
        flexDirection: 'row',
        gap: 12,
    },
    tipInput: {
        flex: 1,
        backgroundColor: "rgba(255,255,255,0.05)",
        borderRadius: 12,
        paddingHorizontal: 16,
        color: '#fff',
        fontSize: 14,
        fontWeight: '600',
    },
    tipSubmitBtn: {
        backgroundColor: '#276EF1',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 12,
        justifyContent: 'center',
    },
    tipSubmitText: {
        color: '#fff',
        fontWeight: '900',
        fontSize: 14,
    },
});
