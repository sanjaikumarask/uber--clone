import React, { useEffect, useState, useRef } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Dimensions } from "react-native";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import * as Location from "expo-location";
import { useAuth } from "../contexts/AuthContext";

const { width, height } = Dimensions.get("window");

export default function HomeScreen({ navigation }: any) {
    const [location, setLocation] = useState<Location.LocationObject | null>(null);
    const [loading, setLoading] = useState(true);
    const mapRef = useRef<MapView>(null);
    const { logout } = useAuth();

    useEffect(() => {
        (async () => {
            let { status } = await Location.requestForegroundPermissionsAsync();
            if (status !== "granted") {
                Alert.alert("Permission to access location was denied");
                return;
            }

            let location = await Location.getCurrentPositionAsync({});
            setLocation(location);
            setLoading(false);
        })();
    }, []);

    const handleLogout = () => {
        logout();
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
            {location && (
                <MapView
                    ref={mapRef}
                    provider={PROVIDER_GOOGLE}
                    style={styles.map}
                    initialRegion={{
                        latitude: location.coords.latitude,
                        longitude: location.coords.longitude,
                        latitudeDelta: 0.02,
                        longitudeDelta: 0.02,
                    }}
                    showsUserLocation={true}
                    showsMyLocationButton={true}
                    showsCompass={true}
                >
                    {/* Add markers later */}
                </MapView>
            )}

            <View style={styles.searchContainer}>
                <Text style={styles.greeting}>Where to?</Text>
                <TouchableOpacity style={styles.searchBox}>
                    <Text style={styles.placeholder}>Search destination</Text>
                </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
                <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#fff",
    },
    center: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
    },
    map: {
        width: width,
        height: height,
    },
    searchContainer: {
        position: "absolute",
        top: 60,
        left: 20,
        right: 20,
        backgroundColor: "#fff",
        borderRadius: 12,
        padding: 20,
        elevation: 5,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
    },
    greeting: {
        fontSize: 20,
        fontWeight: "bold",
        marginBottom: 10,
    },
    searchBox: {
        backgroundColor: "#f0f0f0",
        padding: 15,
        borderRadius: 8,
    },
    placeholder: {
        color: "#666",
        fontSize: 16,
    },
    logoutButton: {
        position: "absolute",
        bottom: 40,
        right: 20,
        backgroundColor: "#fff",
        padding: 10,
        borderRadius: 30,
        elevation: 5,
    },
    logoutText: {
        fontSize: 14,
        fontWeight: "bold",
        color: "red",
    },
});
