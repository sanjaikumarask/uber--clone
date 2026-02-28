import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { api } from './api';

/**
 * Service to handle push notification registration and token management.
 * 
 * NOTE: Starting with SDK 53, Remote Push Notifications are not supported in Expo Go.
 * They require a "Development Build". This code handles that limitation gracefully.
 */

// Configure how notifications are handled when the app is foregrounded
Notifications.setNotificationHandler({
    handleNotification: async (notification: Notifications.Notification) => ({
        shouldPlaySound: true,
        shouldSetBadge: false,
        shouldShowBanner: true,
        shouldShowList: true,
    }),
});

/**
 * Helper to validate if a string is a valid UUID (required for Expo Project ID)
 */
function isValidUUID(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
}

export async function registerForPushNotificationsAsync(): Promise<string | undefined> {
    let token: string | undefined;

    // 1. Android Specific Channel setup
    if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
            name: 'default',
            importance: Notifications.AndroidImportance.MAX,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#FF231F7C',
        });
    }

    // 2. Permission and Token Retrieval
    if (Device.isDevice) {
        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
            const { status } = await Notifications.requestPermissionsAsync();
            finalStatus = status;
        }

        if (finalStatus !== 'granted') {
            console.warn('[Push] Permission not granted for notifications');
            return undefined;
        }

        /**
         * 🚨 CRITICAL: Expo SDK 54+ requires a valid UUID Project ID from EAS.
         * If you haven't run 'eas init', this will not exist.
         */
        const projectId =
            Constants?.expoConfig?.extra?.eas?.projectId ??
            Constants?.easConfig?.projectId ??
            (Constants as any)?.extra?.eas?.projectId ??
            (Constants as any)?.manifest?.extra?.eas?.projectId;

        console.log('[Push] Attempting with Project ID:', projectId);

        if (!projectId || !isValidUUID(projectId)) {
            console.warn(
                '[Push] No valid EAS projectId found. Remote notifications require a development build. ' +
                'Current ID found:', projectId
            );
            // We return undefined instead of calling getExpoPushTokenAsync to avoid a 400 error crash
            return undefined;
        }

        try {
            const tokenResponse = await Notifications.getExpoPushTokenAsync({
                projectId,
            });
            token = tokenResponse.data;
            console.log('[Push] Expo Token obtained successfully');
        } catch (error) {
            // Log error but don't crash
            console.error('[Push] Failed to get Expo token:', error);
        }
    } else {
        console.log('[Push] Push notifications require a physical device');
    }

    return token;
}

/**
 * Update the user's push token on the backend server.
 */
export async function updatePushTokenOnBackend(token: string): Promise<void> {
    try {
        await api.post('/users/push-token/update/', { token });
        console.log('[Push] Token successfully synced with backend');
    } catch (err) {
        console.error('[Push] Failed to sync token with backend:', err);
    }
}
