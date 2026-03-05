import React, { useEffect, useState } from "react";
import { createStackNavigator } from "@react-navigation/stack";
import { NavigationContainer } from "@react-navigation/native";
import { ActivityIndicator, View } from "react-native";
import LoginScreen from "../screens/Login";
import SignupScreen from "../screens/Signup";
import HomeScreen from "../screens/Home";
import { AuthProvider, useAuth } from "../contexts/AuthContext";
import DestinationSearchScreen from "../screens/DestinationSearch";
import ConfirmRideScreen from "../screens/ConfirmRide";
import RideTrackingScreen from "../screens/RideTracking";
import OffersScreen from "../screens/OffersScreen";
import SupportScreen from "../screens/SupportScreen";
import CreateSupportScreen from "../screens/CreateSupportScreen";
import RideSearchingScreen from "../screens/RideSearching";
import RideCompletionScreen from "../screens/RideCompletion";

const Stack = createStackNavigator();

function AppStack() {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return (
            <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#000" }}>
                <ActivityIndicator size="large" color="#276EF1" />
            </View>
        );
    }

    return (
        <NavigationContainer>
            <Stack.Navigator screenOptions={{ headerShown: false }}>
                {!isAuthenticated ? (
                    <>
                        <Stack.Screen name="Login" component={LoginScreen} />
                        <Stack.Screen name="Signup" component={SignupScreen} />
                    </>
                ) : (
                    <>
                        <Stack.Screen name="Home" component={HomeScreen} />
                        <Stack.Screen name="DestinationSearch" component={DestinationSearchScreen} />
                        <Stack.Screen name="ConfirmRide" component={ConfirmRideScreen} />
                        <Stack.Screen name="RideTracking" component={RideTrackingScreen} />
                        <Stack.Screen name="RideSearching" component={RideSearchingScreen} />
                        <Stack.Screen name="RideCompletion" component={RideCompletionScreen} />
                        <Stack.Screen name="Offers" component={OffersScreen} />
                        <Stack.Screen name="Support" component={SupportScreen} />
                        <Stack.Screen name="CreateSupport" component={CreateSupportScreen} />
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
