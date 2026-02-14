import React from "react";
import { StyleSheet, View, Alert } from "react-native";
import { GooglePlacesAutocomplete } from "react-native-google-places-autocomplete";
import { GOOGLE_MAPS_APIKEY } from "../config";
import { SafeAreaView } from "react-native-safe-area-context";

export default function DestinationSearchScreen({ navigation }: any) {
    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.container}>
                <GooglePlacesAutocomplete
                    placeholder="Where to?"
                    nearbyPlacesAPI="GooglePlacesSearch"
                    debounce={400}
                    predefinedPlaces={[
                        {
                            description: 'Little Mount, Chennai',
                            geometry: { location: { lat: 13.0185, lng: 80.2227 } },
                        },
                        {
                            description: 'Anna Nagar, Chennai',
                            geometry: { location: { lat: 13.0850, lng: 80.2100 } },
                        },
                    ] as any[]}
                    fetchDetails={true}
                    enablePoweredByContainer={false}
                    minLength={2}
                    onFail={(error) => console.error("Google Places Error:", error)}
                    textInputProps={{
                        placeholderTextColor: "#666",
                        returnKeyType: "search"
                    }}
                    onPress={(data, details = null) => {
                        console.log("Details", details);
                        console.log("Data", data);
                        // Alert.alert("Selected", data.description);

                        // Navigate back to Home with destination
                        // We will upgrade Home.tsx to handle this param
                        navigation.navigate("Home", {
                            destination: {
                                lat: details?.geometry.location.lat,
                                lng: details?.geometry.location.lng,
                                description: data.description,
                            }
                        });
                    }}
                    query={{
                        key: GOOGLE_MAPS_APIKEY,
                        language: "en",
                    }}
                    styles={{
                        container: {
                            flex: 0,
                        },
                        textInput: {
                            fontSize: 18,
                            backgroundColor: "#eee",
                            borderRadius: 5,
                            height: 50,
                        },
                        listView: {
                            backgroundColor: "white",
                            zIndex: 1000,
                        },
                    }}
                />
            </View>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "white",
        padding: 10,
    },
});
