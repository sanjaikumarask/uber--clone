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
import IncentivesScreen from "../screens/Incentives";
import DocumentUploadScreen from "../screens/DocumentUpload";
import SupportScreen from "../screens/SupportScreen";
import CreateSupportScreen from "../screens/CreateSupportScreen";
import RideHistoryScreen from "../screens/RideHistory";

import RegisterScreen from "../screens/Register";

const Stack = createNativeStackNavigator();

export default function RootNavigator() {
    const { isAuthenticated, loadUser } = useAuthStore();
    const [loading, setLoading] = React.useState(true);

    useEffect(() => {
        loadUser().finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (isAuthenticated) {
            import("../services/notifications").then(({ registerForPushNotificationsAsync, updatePushTokenOnBackend }) => {
                registerForPushNotificationsAsync().then(token => {
                    if (token) {
                        updatePushTokenOnBackend(token);
                    }
                });
            });
        }
    }, [isAuthenticated]);

    if (loading) {
        return null; // or Splash
    }

    return (
        <NavigationContainer>
            <Stack.Navigator screenOptions={{ headerShown: false }}>
                {!isAuthenticated ? (
                    <>
                        <Stack.Screen name="Login" component={LoginScreen} />
                        <Stack.Screen name="Register" component={RegisterScreen} />
                    </>
                ) : (
                    <>
                        <Stack.Screen name="Home" component={HomeScreen} />
                        <Stack.Screen name="RideOffer" component={RideOfferScreen} />
                        <Stack.Screen name="RideTracking" component={RideTrackingScreen} />
                        <Stack.Screen name="Wallet" component={WalletScreen} />
                        <Stack.Screen name="Notifications" component={NotificationsScreen} />
                        <Stack.Screen name="Incentives" component={IncentivesScreen} />
                        <Stack.Screen name="DocumentUpload" component={DocumentUploadScreen} />
                        <Stack.Screen name="Support" component={SupportScreen} />
                        <Stack.Screen name="CreateSupport" component={CreateSupportScreen} />
                        <Stack.Screen name="RideHistory" component={RideHistoryScreen} />
                    </>
                )}
            </Stack.Navigator>
        </NavigationContainer>
    );
}
