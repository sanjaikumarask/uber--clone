import { View, Text, Image, TouchableOpacity, Dimensions } from 'react-native';
import React from 'react';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';

const { width, height } = Dimensions.get('window');

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white, justifyContent: 'space-between', paddingBottom: 48 }}>
      {/* Welcome image */}
      <Image
        source={require('../../assets/images/welcome.jpg')}
        style={{ width, height: height * 0.52 }}
        resizeMode="contain"
      />

      {/* Text */}
      <View style={{ alignItems: 'center', paddingHorizontal: 24 }}>
        <Text style={{ fontSize: 32, fontWeight: '800', color: Colors.textDark, marginBottom: 10 }}>Welcome</Text>
        <Text style={{ fontSize: 16, color: Colors.textMuted, textAlign: 'center' }}>Have a better sharing experience</Text>
      </View>

      {/* Buttons */}
      <View style={{ paddingHorizontal: 24, gap: 14 }}>
        <TouchableOpacity
          onPress={() => router.push('/(auth)/signup')}
          style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Sign Up</Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => router.push('/(auth)/login')}
          style={{ borderWidth: 1.5, borderColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.primary }}>Log In</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
