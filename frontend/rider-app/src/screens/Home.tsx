import React, { useEffect, useState, useRef } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, Dimensions } from "react-native";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import * as Location from "expo-location";
import { useAuth } from "../contexts/AuthContext";
// import MapViewDirections from "react-native-maps-directions"; // Maybe later
import { GOOGLE_MAPS_APIKEY } from "../config";

const { width, height } = Dimensions.get("window");

export default function HomeScreen({ navigation, route }: any) {
    const [location, setLocation] = useState<Location.LocationObject | null>(null);
    const [loading, setLoading] = useState(true);
    const mapRef = useRef<MapView>(null);
    const { logout } = useAuth();

    // Check for destination from Params
    const destination = route.params?.destination;

    useEffect(() => {
        if (destination && location && mapRef.current) {
            // Fit to coordinates
            mapRef.current.fitToCoordinates([
                { latitude: location.coords.latitude, longitude: location.coords.longitude },
                { latitude: destination.lat, longitude: destination.lng }
            ], {
                edgePadding: { top: 100, right: 50, bottom: 50, left: 50 },
                animated: true
            });
        }
    }, [destination, location]);

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
                    {destination && (
                        <Marker
                            coordinate={{ latitude: destination.lat, longitude: destination.lng }}
                            title={destination.description}
                        />
                    )}
                </MapView>
            )}

            <View style={styles.searchContainer}>
                <Text style={styles.greeting}>{destination ? "To:" : "Where to?"}</Text>
                <TouchableOpacity
                    style={styles.searchBox}
                    onPress={() => navigation.navigate("DestinationSearch")}
                >
                    <Text style={styles.placeholder} numberOfLines={1}>
                        {destination ? destination.description : "Search destination"}
                    </Text>
                </TouchableOpacity>
            </View>

            {destination && (
                <TouchableOpacity
                    style={styles.confirmButton}
                    onPress={() => navigation.navigate("ConfirmRide", { destination })}
                >
                    <Text style={styles.confirmText}>Confirm Ride</Text>
                </TouchableOpacity>
            )}

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
    confirmButton: {
        position: "absolute",
        bottom: 100,
        left: 20,
        right: 20,
        backgroundColor: "#000",
        padding: 15,
        borderRadius: 8,
        alignItems: "center",
        elevation: 5,
    },
    confirmText: {
        color: "#fff",
        fontSize: 18,
        fontWeight: "bold",
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
