import React, { useEffect, useState, useRef } from "react";
import { View, Text, StyleSheet, ActivityIndicator, Alert, Dimensions, TouchableOpacity, ScrollView, TextInput } from "react-native";
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from "react-native-maps";
import { api, WS_URL } from "../services/api";
import { Storage } from "../services/storage";
import { decodePolyline } from "../services/utils";

const { width, height } = Dimensions.get("window");

// 🗺️ Rider Web-like Minimalist Style (Light)
const mapStyle = [
    { "elementType": "geometry", "stylers": [{ "color": "#f5f5f5" }] },
    { "elementType": "labels.icon", "stylers": [{ "visibility": "off" }] },
    { "elementType": "labels.text.fill", "stylers": [{ "color": "#616161" }] },
    { "elementType": "labels.text.stroke", "stylers": [{ "color": "#f5f5f5" }] },
    { "featureType": "road", "elementType": "geometry", "stylers": [{ "color": "#ffffff" }] },
    { "featureType": "road.highway", "elementType": "geometry", "stylers": [{ "color": "#dadada" }] },
    { "featureType": "water", "elementType": "geometry", "stylers": [{ "color": "#c9c9c9" }] }
];

export default function RideTrackingScreen({ navigation, route }: any) {
    const { rideId } = route.params;
    const [ride, setRide] = useState<any>(null);
    const [status, setStatus] = useState("SEARCHING");
    const [path, setPath] = useState<any[]>([]);
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const mapRef = useRef<MapView>(null);

    useEffect(() => {
        let ws: WebSocket | null = null;
        let reconnectTimeout: any = null;
        let retryCount = 0;
        let isActive = true;

        const connectWebSocket = async () => {
            if (!isActive) return;

            const token = await Storage.getToken();
            if (!token) {
                console.error("No token found for WS");
                return;
            }

            const wsUrl = `${WS_URL}/rides/${rideId}/?token=${token}`;
            console.log("🔌 Connecting to:", wsUrl);
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("✅ Ride WS Connected");
                retryCount = 0; // Reset backoff on success
            };

            ws.onerror = (err) => {
                console.error("❌ WS Error. Retrying...");
                ws?.close(); // Force close to trigger onclose logic
            };

            ws.onclose = (e) => {
                console.warn(`⚠️ WS Closed. Code: ${e.code}, Reason: ${e.reason}`);

                if (isActive) {
                    const backoffTime = Math.min(1000 * Math.pow(2, retryCount), 15000); // Max 15 seconds
                    retryCount++;
                    console.log(`⏱️ Auto-reconnecting in ${backoffTime / 1000} seconds...`);

                    if (reconnectTimeout) clearTimeout(reconnectTimeout);
                    reconnectTimeout = setTimeout(() => connectWebSocket(), backoffTime);
                }
            };

            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    console.log("📥 WS Message:", data.type);

                    if (data.type === "ride_update" || data.type === "WS_CONNECTED" || data.type === "RIDE_STATUS_UPDATED" || data.type === "RIDE_COMPLETED") {
                        const rideData = data.payload?.ride || data.ride || data.payload;
                        if (rideData) {
                            console.log("🚦 Status Update:", rideData.status, "OTP:", rideData.otp_code);
                            setRide((prev: any) => ({ ...prev, ...rideData }));
                            if (rideData.status) setStatus(rideData.status);

                            if (rideData.polyline || rideData.planned_route_polyline) {
                                setPath(decodePolyline(rideData.polyline || rideData.planned_route_polyline));
                            }

                            if (rideData.status === "COMPLETED" || data.type === "RIDE_COMPLETED") {
                                console.log("🏁 Ride Completed, navigating...");
                                navigation.replace("RideCompletion", { rideId });
                            }
                        }
                    } else if (data.type === "location_update" || data.type === "DRIVER_LOCATION_UPDATED") {
                        const locData = data.payload || data;
                        setRide((prev: any) => {
                            if (!prev) return null;
                            return {
                                ...prev,
                                driver: {
                                    ...(prev.driver || {}),
                                    lat: locData.lat,
                                    lng: locData.lng,
                                    heading: locData.heading,
                                    eta: locData.eta
                                }
                            };
                        });
                    }
                } catch (err) {
                    console.error("Failed to parse WS message", err);
                }
            };

            setSocket(ws);
        };

        const setup = async () => {
            fetchRideDetails();
            connectWebSocket();
        };

        setup();

        // 🔄 Polling Fallback (ensures UI updates even if WS fails)
        const pollInterval = setInterval(() => {
            if (isActive) fetchRideDetails();
        }, 10000);

        return () => {
            isActive = false;
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            if (ws) {
                ws.onclose = () => { }; // remove listener to avoid reconnect loop on destroy
                ws.close();
            }
            clearInterval(pollInterval);
        };
    }, [rideId]);

    useEffect(() => {
        if (ride && mapRef.current) {
            const coords = [
                { latitude: parseFloat(ride.pickup_lat), longitude: parseFloat(ride.pickup_lng) },
                { latitude: parseFloat(ride.drop_lat), longitude: parseFloat(ride.drop_lng) },
            ];

            if (ride.driver?.lat && ride.driver?.lng) {
                coords.push({ latitude: parseFloat(ride.driver.lat), longitude: parseFloat(ride.driver.lng) });
            }

            mapRef.current.fitToCoordinates(coords, {
                edgePadding: { top: 100, right: 80, bottom: 300, left: 80 },
                animated: true,
            });
        }
    }, [ride]);

    const fetchRideDetails = async () => {
        try {
            const res = await api.get(`/rides/${rideId}/`);
            setRide(res.data);
            setStatus(res.data.status);
            if (res.data.status === "COMPLETED") {
                navigation.replace("RideCompletion", { rideId });
                return;
            }
            if (res.data.planned_route_polyline || res.data.polyline) {
                setPath(decodePolyline(res.data.planned_route_polyline || res.data.polyline));
            }
        } catch (err) {
            console.error("Fetch ride failed", err);
        }
    };

    const getStatusMessage = () => {
        switch (status) {
            case "SEARCHING": return "Finding you a driver...";
            case "OFFERED": return "Contacting drivers...";
            case "ASSIGNED": return "Driver is on the way!";
            case "ARRIVED": return "Driver has arrived!";
            case "ONGOING": return "Ride in progress";
            case "COMPLETED": return "Ride completed";
            default: return status;
        }
    };

    const handleSOS = async () => {
        Alert.alert(
            "Emergency SOS",
            "Are you in danger?",
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Trigger SOS",
                    style: "destructive",
                    onPress: async () => {
                        try {
                            const lat = ride.driver?.lat || ride.pickup_lat;
                            const lng = ride.driver?.lng || ride.pickup_lng;
                            await api.post(`/supports/rides/${rideId}/sos/`, { lat, lng });
                            Alert.alert("SOS Triggered", "Help is on the way.");
                        } catch (err) {
                            Alert.alert("Error", "Failed to trigger SOS.");
                        }
                    }
                }
            ]
        );
    };

    const [chatOpen, setChatOpen] = useState(false);
    const [messages, setMessages] = useState<any[]>([]);
    const [newMessage, setNewMessage] = useState("");

    useEffect(() => {
        if (!socket) return;

        const handleMessage = (e: any) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === "NEW_CHAT_MESSAGE") {
                    const msg = data.payload || data;
                    setMessages(prev => [...prev, msg]);
                }
            } catch (err) {
                console.error("Chat message parse error", err);
            }
        };

        const oldOnMessage = socket.onmessage;
        socket.onmessage = (e) => {
            handleMessage(e);
            if (oldOnMessage) oldOnMessage.call(socket, e);
        };
    }, [socket]);

    const sendMessage = () => {
        if (!newMessage.trim() || !socket) return;
        socket.send(JSON.stringify({
            type: "SEND_CHAT",
            message: newMessage
        }));
        setNewMessage("");
    };

    if (!ride) return (
        <View style={styles.center}>
            <ActivityIndicator size="large" color="#000" />
            <Text style={{ marginTop: 10 }}>Loading ride details...</Text>
        </View>
    );

    return (
        <View style={styles.container}>
            <MapView
                ref={mapRef}
                provider={PROVIDER_GOOGLE}
                style={styles.map}
                customMapStyle={mapStyle}
                initialRegion={{
                    latitude: parseFloat(ride.pickup_lat),
                    longitude: parseFloat(ride.pickup_lng),
                    latitudeDelta: 0.05,
                    longitudeDelta: 0.05,
                }}
                showsCompass={false}
                showsUserLocation={true}
            >
                <Marker coordinate={{ latitude: parseFloat(ride.pickup_lat), longitude: parseFloat(ride.pickup_lng) }} title="Pickup" />
                <Marker coordinate={{ latitude: parseFloat(ride.drop_lat), longitude: parseFloat(ride.drop_lng) }} title="Dropoff" pinColor="red" />

                {ride.driver && ride.driver.lat && ride.driver.lng && (
                    <Marker
                        coordinate={{ latitude: parseFloat(ride.driver.lat), longitude: parseFloat(ride.driver.lng) }}
                        anchor={{ x: 0.5, y: 0.5 }}
                    >
                        <View style={styles.driverMarker}>
                            <Text style={{ fontSize: 18 }}>🚕</Text>
                        </View>
                    </Marker>
                )}

                {path.length > 0 && (
                    <Polyline
                        coordinates={path}
                        strokeWidth={5}
                        strokeColor="#333"
                    />
                )}
            </MapView>

            <View style={styles.panel}>
                <View style={styles.handle} />
                <Text style={styles.statusTitle}>{getStatusMessage()}</Text>

                <View style={styles.driverInfo}>
                    <View style={styles.driverMainRow}>
                        <View style={styles.avatar}>
                            <Text style={styles.avatarText}>
                                {ride.driver?.user?.first_name?.[0] || ride.driver?.user?.username?.[0] || "D"}
                            </Text>
                        </View>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.driverName}>
                                {ride.driver?.user?.first_name
                                    ? `${ride.driver.user.first_name} ${ride.driver?.user?.last_name || ""}`
                                    : ride.driver?.user?.username || "Your Driver"}
                            </Text>
                            <View style={styles.driverMeta}>
                                <Text style={styles.ratingText}>★ 4.9</Text>
                                <Text style={styles.vehicleText}>{ride.driver?.vehicle_model || "UberGo"}</Text>
                            </View>
                            <View style={styles.plateBadge}>
                                <Text style={styles.plateText}>{ride.driver?.vehicle_number || "TN-01-AB-1234"}</Text>
                            </View>
                        </View>
                        {ride.vehicle_type && (
                            <Text style={{ fontSize: 40 }}>
                                {ride.vehicle_type === 'moto' ? '🏍️' : ride.vehicle_type === 'auto' ? '🛺' : ride.vehicle_type === 'xl' ? '🚙' : '🚗'}
                            </Text>
                        )}
                    </View>
                </View>

                <View style={styles.divider} />

                {status === "ARRIVED" ? (
                    <View style={styles.otpSection}>
                        <Text style={styles.otpLabel}>SHARE WITH DRIVER</Text>
                        <Text style={styles.otpValue}>{ride.otp_code || "----"}</Text>
                        <View style={styles.arrivalBadge}>
                            <Text style={styles.arrivalText}>Driver Has Arrived</Text>
                        </View>
                    </View>
                ) : (
                    <View style={styles.addressSection}>
                        <View style={styles.addressRow}>
                            <View style={[styles.dot, { backgroundColor: "#276EF1" }]} />
                            <Text style={styles.addressText} numberOfLines={1}>{ride.pickup_address || "Pickup..."}</Text>
                        </View>
                        <View style={styles.verticalLine} />
                        <View style={styles.addressRow}>
                            <View style={[styles.dot, { backgroundColor: "#22c55e" }]} />
                            <Text style={styles.addressText} numberOfLines={1}>{ride.drop_address || "Destination..."}</Text>
                        </View>
                    </View>
                )}

                <View style={styles.actionRow}>
                    <TouchableOpacity style={styles.actionBtn} onPress={() => setChatOpen(true)}>
                        <Text style={styles.actionBtnText}>💬 Message</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.actionBtn} onPress={handleSOS}>
                        <Text style={[styles.actionBtnText, { color: '#ef4444' }]}>🛡️ Safety</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate("CreateSupport", { rideId: ride.id })}>
                        <Text style={styles.actionBtnText}>✕ Cancel</Text>
                    </TouchableOpacity>
                </View>
            </View>

            {/* Basic Chat Modal */}
            {chatOpen && (
                <View style={styles.chatOverlay}>
                    <View style={styles.chatHeader}>
                        <Text style={styles.chatTitle}>Chat with Driver</Text>
                        <TouchableOpacity onPress={() => setChatOpen(false)}><Text style={{ color: '#fff' }}>Close</Text></TouchableOpacity>
                    </View>
                    <ScrollView style={{ flex: 1, padding: 16 }}>
                        {messages.map((m, i) => (
                            <View key={i} style={[styles.msgBubble, m.sender_id === ride.rider_id ? styles.msgRider : styles.msgDriver]}>
                                <Text style={styles.msgText}>{m.message}</Text>
                            </View>
                        ))}
                    </ScrollView>
                    <View style={styles.chatInputRow}>
                        <View style={styles.inputWrap}>
                            <TextInput
                                style={styles.input}
                                value={newMessage}
                                onChangeText={setNewMessage}
                                placeholder="Type a message..."
                                placeholderTextColor="#666"
                            />
                        </View>
                        <TouchableOpacity style={styles.sendBtn} onPress={sendMessage}>
                            <Text style={{ color: '#fff', fontWeight: 'bold' }}>Send</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#000' },
    center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: '#0A0A0A' },
    map: { flex: 1 },
    driverMarker: {
        backgroundColor: "rgba(0,0,0,0.85)",
        borderRadius: 20,
        padding: 4,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.2)'
    },
    panel: {
        backgroundColor: "rgba(10,10,10,0.98)",
        padding: 24,
        paddingBottom: 40,
        borderTopLeftRadius: 32,
        borderTopRightRadius: 32,
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        elevation: 20,
        borderTopWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
    },
    handle: {
        width: 40,
        height: 4,
        backgroundColor: "rgba(255,255,255,0.15)",
        borderRadius: 10,
        alignSelf: "center",
        marginBottom: 20,
    },
    statusTitle: { fontSize: 24, fontWeight: "900", marginBottom: 16, color: "#FFFFFF", textAlign: 'center' },
    driverInfo: {
        padding: 0,
        width: "100%",
    },
    driverMainRow: {
        flexDirection: "row",
        alignItems: "center",
        gap: 16,
    },
    avatar: {
        width: 54,
        height: 54,
        borderRadius: 27,
        backgroundColor: "rgba(255,255,255,0.08)",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.15)",
        alignItems: "center",
        justifyContent: "center",
    },
    avatarText: { color: "#fff", fontSize: 20, fontWeight: "800" },
    driverName: { fontWeight: "800", fontSize: 18, color: "#FFFFFF", marginBottom: 2 },
    driverMeta: { flexDirection: "row", gap: 8, alignItems: "center" },
    ratingText: { color: "#FFCC00", fontWeight: "700", fontSize: 13 },
    vehicleText: { color: "#A6A6A6", fontSize: 13 },
    plateBadge: {
        backgroundColor: "rgba(255,255,255,0.08)",
        alignSelf: "flex-start",
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 4,
        marginTop: 6,
    },
    plateText: { color: "#A6A6A6", fontSize: 11, fontWeight: "800", letterSpacing: 1 },
    divider: {
        height: 1,
        backgroundColor: "rgba(255,255,255,0.08)",
        width: '100%',
        marginVertical: 20,
    },
    addressSection: { width: '100%' },
    addressRow: { flexDirection: "row", alignItems: "center", gap: 12 },
    dot: { width: 8, height: 8, borderRadius: 4 },
    addressText: { color: "#A6A6A6", fontSize: 14, fontWeight: "500", flex: 1 },
    verticalLine: {
        width: 1,
        height: 16,
        backgroundColor: "rgba(255,255,255,0.15)",
        marginLeft: 3.5,
        marginVertical: 4,
    },
    otpSection: {
        alignItems: "center",
        width: "100%",
    },
    otpLabel: {
        fontSize: 10,
        fontWeight: "900",
        color: "#A6A6A6",
        letterSpacing: 2,
        marginBottom: 8,
    },
    otpValue: {
        fontSize: 48,
        fontWeight: "900",
        color: "#22c55e",
        letterSpacing: 12,
        marginBottom: 16,
    },
    arrivalBadge: {
        backgroundColor: "rgba(34, 197, 94, 0.1)",
        paddingVertical: 8,
        paddingHorizontal: 16,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: "rgba(34, 197, 94, 0.2)",
    },
    arrivalText: {
        color: "#22c55e",
        fontSize: 12,
        fontWeight: "900",
        textTransform: "uppercase",
    },
    actionRow: {
        flexDirection: "row",
        gap: 10,
        width: "100%",
        marginTop: 24,
        paddingTop: 20,
        borderTopWidth: 1,
        borderColor: "rgba(255,255,255,0.06)",
    },
    actionBtn: {
        flex: 1,
        backgroundColor: "rgba(255,255,255,0.05)",
        paddingVertical: 14,
        borderRadius: 12,
        alignItems: "center",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.08)",
    },
    actionBtnText: { color: "#FFFFFF", fontWeight: "700", fontSize: 13 },
    chatOverlay: {
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: '#000',
        zIndex: 1000,
    },
    chatHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 20,
        paddingTop: 60,
        borderBottomWidth: 1,
        borderColor: 'rgba(255,255,255,0.1)',
        backgroundColor: '#0a0a0a',
    },
    chatTitle: { color: '#fff', fontSize: 18, fontWeight: '700' },
    msgBubble: {
        padding: 12,
        borderRadius: 16,
        marginBottom: 10,
        maxWidth: '80%',
    },
    msgRider: {
        backgroundColor: '#276EF1',
        alignSelf: 'flex-end',
        borderBottomRightRadius: 4,
    },
    msgDriver: {
        backgroundColor: 'rgba(255,255,255,0.08)',
        alignSelf: 'flex-start',
        borderBottomLeftRadius: 4,
    },
    msgText: { color: '#fff', fontSize: 14 },
    chatInputRow: {
        flexDirection: 'row',
        padding: 16,
        paddingBottom: 40,
        borderTopWidth: 1,
        borderColor: 'rgba(255,255,255,0.1)',
        backgroundColor: '#0a0a0a',
        alignItems: 'center',
        gap: 12,
    },
    inputWrap: {
        flex: 1,
        backgroundColor: 'rgba(255,255,255,0.05)',
        borderRadius: 24,
        paddingHorizontal: 16,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.1)',
    },
    input: { height: 44, color: '#fff' },
    sendBtn: {
        backgroundColor: '#276EF1',
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 20,
    },
});
