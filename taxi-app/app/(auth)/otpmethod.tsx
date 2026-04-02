import { View, Text, TouchableOpacity } from 'react-native';
import React, { useState } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Colors from '../../constants/Colors';


export default function OtpMethodScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ 
    value: string; 
    masked_phone?: string; 
    masked_email?: string;
    phone?: string;
    email?: string;
  }>();
  
  const { value, masked_phone, masked_email, phone, email } = params;
  const [selected, setSelected] = useState<'sms' | 'email'>(masked_email ? 'email' : 'sms');

  const handleContinue = () => {
    // If user chose email, we pass the real email to otpverify
    const finalValue = selected === 'email' ? email : phone;
    router.push({ 
      pathname: '/(auth)/otpverify', 
      params: { value: finalValue || value } 
    });
  };

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white, paddingHorizontal: 24, paddingTop: 64 }}>

      {/* Title */}
      <Text style={{ fontSize: 30, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 12 }}>
        Forgot Password
      </Text>
      <Text style={{ fontSize: 15, color: Colors.textMuted, textAlign: 'center', lineHeight: 22, marginBottom: 40 }}>
        Select which contact details should{'\n'}we use to reset your password
      </Text>

      <View style={{ gap: 16 }}>
        {/* Via SMS — show only if user has phone */}
        {masked_phone && (
          <TouchableOpacity
            onPress={() => setSelected('sms')}
            style={{
              flexDirection: 'row', alignItems: 'center',
              borderWidth: 1.5,
              borderColor: selected === 'sms' ? Colors.primary : Colors.primaryBorder,
              backgroundColor: selected === 'sms' ? '#FFFDE7' : Colors.white,
              borderRadius: 14, padding: 16, gap: 16,
            }}
          >
            <View style={{
              width: 52, height: 52, borderRadius: 26,
              borderWidth: 1.5, borderColor: Colors.primary,
              backgroundColor: selected === 'sms' ? Colors.primary : Colors.white,
              alignItems: 'center', justifyContent: 'center',
            }}>
              <Ionicons name="chatbubble-ellipses" size={24} color={selected === 'sms' ? Colors.white : Colors.primary} />
            </View>
            <View>
              <Text style={{ fontSize: 14, color: Colors.textMuted, marginBottom: 4 }}>Via SMS</Text>
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark }}>{masked_phone}</Text>
            </View>
          </TouchableOpacity>
        )}

        {/* Via Email — show only if user has email */}
        {masked_email && (
          <TouchableOpacity
            onPress={() => setSelected('email')}
            style={{
              flexDirection: 'row', alignItems: 'center',
              borderWidth: 1.5,
              borderColor: selected === 'email' ? Colors.primary : Colors.primaryBorder,
              backgroundColor: selected === 'email' ? '#FFFDE7' : Colors.white,
              borderRadius: 16, padding: 18, gap: 16,
            }}
          >
            <View style={{
              width: 52, height: 52, borderRadius: 26,
              borderWidth: 1.5, borderColor: Colors.primary,
              backgroundColor: selected === 'email' ? Colors.primary : Colors.white,
              alignItems: 'center', justifyContent: 'center',
            }}>
              <Ionicons name="mail" size={24} color={selected === 'email' ? Colors.white : Colors.primary} />
            </View>
            <View>
              <Text style={{ fontSize: 14, color: Colors.textMuted, marginBottom: 4 }}>Via Email</Text>
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark }}>{masked_email}</Text>
            </View>
          </TouchableOpacity>
        )}
      </View>

      {/* Continue button */}
      <View style={{ position: 'absolute', bottom: 32, left: 24, right: 24 }}>
        <TouchableOpacity
          onPress={handleContinue}
          style={{ backgroundColor: Colors.primary, borderRadius: 16, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Continue</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
