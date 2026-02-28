import { Audio, AVPlaybackStatus } from 'expo-av';

/**
 * Service to handle notification sounds in the driver app.
 */

const NOTIFICATION_SOUND_URL = "https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3";

export async function playNotificationSound(): Promise<void> {
    try {
        // Ensure audio is enabled
        await Audio.setAudioModeAsync({
            playsInSilentModeIOS: true,
            staysActiveInBackground: true,
            shouldDuckAndroid: true,
        });

        const { sound } = await Audio.Sound.createAsync(
            { uri: NOTIFICATION_SOUND_URL },
            { shouldPlay: true, volume: 1.0 }
        );

        // Automatically unload sound from memory when it finishes playing
        sound.setOnPlaybackStatusUpdate((status: AVPlaybackStatus) => {
            if (status.isLoaded && status.didJustFinish) {
                sound.unloadAsync().catch((err: Error) => console.error('[Sound] Unload error:', err));
            }
        });

        await sound.playAsync();
    } catch (error) {
        console.error('[Sound] Failed to play notification sound:', error);
    }
}
