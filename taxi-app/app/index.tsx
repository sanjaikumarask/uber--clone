import { useEffect, useState } from 'react';
import { View, ActivityIndicator, Platform } from 'react-native';
import { Redirect } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import Colors from '../constants/Colors';

const STORAGE_KEY = 'onboarding_device_id';

export default function Index() {
  const [ready, setReady] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    (async () => {
      let id: string = 'unknown';
      if (Platform.OS === 'android') {
        id = Application.getAndroidId() ?? Device.modelId ?? Device.deviceName ?? 'unknown';
      } else if (Platform.OS === 'ios') {
        id = (await Application.getIosIdForVendorAsync()) ?? Device.modelId ?? Device.deviceName ?? 'unknown';
      } else {
        id = Device.modelId ?? Device.deviceName ?? 'unknown';
      }
      const stored = await AsyncStorage.getItem(STORAGE_KEY);

      if (stored !== id) {
        await AsyncStorage.setItem(STORAGE_KEY, id as string);
        setShowOnboarding(true);
      }

      setReady(true);
    })();
  }, []);

  if (!ready) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.white }}>
        <ActivityIndicator color={Colors.primary} />
      </View>
    );
  }

  return <Redirect href={showOnboarding ? '/(auth)/onboarding' : '/(auth)/welcome'} />;
}
