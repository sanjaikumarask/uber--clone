import React, { useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useAuthStore } from "../domains/auth/auth.store";
import LoginScreen from "../screens/Login";
import HomeScreen from "../screens/Home";
import RideOfferScreen from "../screens/RideOffer";
import RideTrackingScreen from "../screens/RideTracking";
import WalletScreen from "../screens/Wallet";
import NotificationsScreen from "../screens/Notifications";

const Stack = createNativeStackNavigator();

export default function RootNavigator() {
    const { isAuthenticated, loadUser } = useAuthStore();
    const [loading, setLoading] = React.useState(true);

    useEffect(() => {
        loadUser().finally(() => setLoading(false));
    }, []);

    if (loading) {
        return null; // or Splash
    }

    return (
        <NavigationContainer>
            <Stack.Navigator screenOptions={{ headerShown: false }}>
                {!isAuthenticated ? (
                    <Stack.Screen name="Login" component={LoginScreen} />
                ) : (
                    <>
                        <Stack.Screen name="Home" component={HomeScreen} />
                        <Stack.Screen name="RideOffer" component={RideOfferScreen} />
                        <Stack.Screen name="RideTracking" component={RideTrackingScreen} />
                        <Stack.Screen name="Wallet" component={WalletScreen} />
                        <Stack.Screen name="Notifications" component={NotificationsScreen} />
                    </>
                )}
            </Stack.Navigator>
        </NavigationContainer>
    );
}
