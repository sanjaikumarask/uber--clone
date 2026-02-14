import React, { useEffect, useState } from "react";
import { createStackNavigator } from "@react-navigation/stack";
import { NavigationContainer } from "@react-navigation/native";
import { ActivityIndicator, View } from "react-native";
import LoginScreen from "../screens/Login";
import HomeScreen from "../screens/Home";
import { AuthProvider, useAuth } from "../contexts/AuthContext";
import DestinationSearchScreen from "../screens/DestinationSearch";
import ConfirmRideScreen from "../screens/ConfirmRide";
import RideTrackingScreen from "../screens/RideTracking";

const Stack = createStackNavigator();

function AppStack() {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return (
            <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
                <ActivityIndicator size="large" color="#000" />
            </View>
        );
    }

    return (
        <NavigationContainer>
            <Stack.Navigator screenOptions={{ headerShown: false }}>
                {!isAuthenticated ? (
                    <Stack.Screen name="Login" component={LoginScreen} />
                ) : (
                    <>
                        <Stack.Screen name="Home" component={HomeScreen} />
                        <Stack.Screen name="DestinationSearch" component={DestinationSearchScreen} />
                        <Stack.Screen name="ConfirmRide" component={ConfirmRideScreen} />
                        <Stack.Screen name="RideTracking" component={RideTrackingScreen} />
                    </>
                )}
            </Stack.Navigator>
        </NavigationContainer>
    );
}

export default function RootNavigation() {
    return (
        <AuthProvider>
            <AppStack />
        </AuthProvider>
    );
}
