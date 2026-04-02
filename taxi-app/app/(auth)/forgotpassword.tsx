import { View, Text, TextInput, TouchableOpacity, KeyboardAvoidingView, TouchableWithoutFeedback, Keyboard, Alert, ActivityIndicator } from 'react-native';
import React, { useState } from 'react';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!value.trim()) {
      Alert.alert('Please enter your email or phone number.');
      return;
    }
    
    try {
      setLoading(true);
      const res = await api.post('/users/forgot-password/', { phone: value.trim() });
      const { masked_phone, masked_email, phone, email } = res.data;
      
      router.push({ 
        pathname: '/(auth)/otpmethod', 
        params: { 
          value: value.trim(),
          masked_phone: masked_phone || '',
          masked_email: masked_email || '',
          phone: phone || '',
          email: email || '',
        } 
      });
    } catch (err: any) {
      console.error('Forgot PW Error:', err.response?.data || err.message);
      Alert.alert('Request Failed', 'Could not find account. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior="padding">
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <View style={{ flex: 1, paddingHorizontal: 24, paddingTop: 64 }}>

          {/* Title */}
          <Text style={{ fontSize: 32, fontWeight: '700', color: Colors.textDark, marginBottom: 36, lineHeight: 42 }}>
            Verification email or phone number
          </Text>

          {/* Input */}
          <View style={{
            flexDirection: 'row', alignItems: 'center',
            borderWidth: 1.5, borderColor: '#D0D0D0',
            borderRadius: 10, paddingHorizontal: 16, paddingVertical: 14,
          }}>
            <TextInput
              value={value}
              onChangeText={setValue}
              placeholder="Email OR Phone Number"
              placeholderTextColor={Colors.textPlaceholder}
              keyboardType="email-address"
              autoCapitalize="none"
              style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
            />
          </View>

          {/* Send OTP button — pinned to bottom */}
          <View style={{ position: 'absolute', bottom: 32, left: 24, right: 24 }}>
            <TouchableOpacity
              onPress={handleSend}
              style={{ backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
            >
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Send OTP</Text>
            </TouchableOpacity>
          </View>

        </View>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}
