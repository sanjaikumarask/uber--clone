import { Stack } from 'expo-router';
import "../global.css";
import 'react-native-reanimated';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import { Platform } from 'react-native';
import { FavouriteProvider } from '../context/FavouriteContext';

export const unstable_settings = {
  anchor: '(auth)',
};

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <SafeAreaView style={{ flex: 1 }} edges={Platform.OS === 'android' ? ['top', 'bottom'] : ['top']}>
        <FavouriteProvider>
          <Stack>
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="(auth)" options={{ headerShown: false }} />
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="screens" options={{ headerShown: false }} />
          </Stack>
        </FavouriteProvider>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
