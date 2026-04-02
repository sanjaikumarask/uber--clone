import { View, Text, TextInput, TouchableOpacity, Alert, TouchableWithoutFeedback, Keyboard, ActivityIndicator } from 'react-native';
import React, { useRef, useState } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import { Storage } from '../../services/storage';

const OTP_LENGTH = 6;

export default function OtpVerifyScreen() {
  const router = useRouter();
  const { value = '', type = 'forgot_password', signupData = '' } = useLocalSearchParams<{ value: string; type: string; signupData: string }>();
  const [otp, setOtp] = useState<string[]>(Array(OTP_LENGTH).fill(''));
  const [loading, setLoading] = useState(false);
  const inputs = useRef<(TextInput | null)[]>([]);

  const handleChange = (text: string, index: number) => {
    const digit = text.replace(/[^0-9]/g, '').slice(-1);
    const newOtp = [...otp];
    newOtp[index] = digit;
    setOtp(newOtp);
    if (digit && index < OTP_LENGTH - 1) {
      inputs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (e: any, index: number) => {
    if (e.nativeEvent.key === 'Backspace' && !otp[index] && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  const handleVerify = async () => {
    const otpStr = otp.join('');
    if (otpStr.length < OTP_LENGTH) {
      Alert.alert('Please enter the complete OTP.');
      return;
    }

    try {
      setLoading(true);
      if (type === 'signup') {
        const data = JSON.parse(signupData);
        // Backend now handles verification in the /register POST
        const res = await api.post('users/register/', { 
          ...data, 
          otp: otpStr,
          email: value 
        });
        
        Alert.alert('Welcome!', 'Your account has been created successfully. Please log in with your credentials.', [
          { text: 'Log In', onPress: () => router.replace('/(auth)/login') }
        ]);
      } else {
        // Forgot Password flow — Verify OTP FIRST before going to reset screen
        await api.post('users/verify-otp/', {
            phone: value,
            otp: otpStr
        });

        router.push({ 
            pathname: '/(auth)/resetpassword', 
            params: { 
                value: value,
                otp: otpStr 
            } 
        });
      }
    } catch (err: any) {
      console.error('Verification Failed:', err.response?.data || err.message);
      const msg = err.response?.data?.error || 'Invalid or expired code. Please try again.';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = () => {
    setOtp(Array(OTP_LENGTH).fill(''));
    inputs.current[0]?.focus();
    Alert.alert('OTP Resent', 'A new OTP has been sent.');
  };

  const maskedValue = value.includes('@')
    ? '**** **** **** ' + value.split('@')[1]
    : '**** ***' + value.slice(-2);

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <View style={{ flex: 1, backgroundColor: Colors.white, paddingHorizontal: 24, paddingTop: 64 }}>

      {/* Title */}
      <Text style={{ fontSize: 30, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 12 }}>
        {type === 'signup' ? 'Verification' : 'Forgot Password'}
      </Text>
      <Text style={{ fontSize: 15, color: Colors.textMuted, textAlign: 'center', marginBottom: 40 }}>
        {type === 'signup' ? 'Verification' : 'OTP'} Code has been send to {maskedValue}
      </Text>

      {/* OTP boxes */}
      <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 12, marginBottom: 28 }}>
        {otp.map((digit, index) => (
          <TextInput
            key={index}
            ref={(r) => { inputs.current[index] = r; }}
            value={digit}
            onChangeText={(t) => handleChange(t, index)}
            onKeyPress={(e) => handleKeyPress(e, index)}
            keyboardType="number-pad"
            maxLength={1}
            style={{
              width: 52, height: 52,
              borderWidth: 1.5,
              borderColor: digit ? Colors.primary : '#D0D0D0',
              borderRadius: 14,
              textAlign: 'center',
              fontSize: 22, fontWeight: '700',
              color: Colors.textDark,
              backgroundColor: Colors.white,
            }}
          />
        ))}
      </View>

      {/* Resend */}
      <View style={{ flexDirection: 'row', justifyContent: 'center' }}>
        <Text style={{ fontSize: 15, color: Colors.textDark, fontWeight: '600' }}>Didn't receive code? </Text>
        <TouchableOpacity onPress={handleResend}>
          <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.primary }}>Resend again</Text>
        </TouchableOpacity>
      </View>

      {/* Verify button */}
      <View style={{ position: 'absolute', bottom: 32, left: 24, right: 24 }}>
        <TouchableOpacity
          onPress={handleVerify}
          style={{ backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Verify</Text>
        </TouchableOpacity>
      </View>

      </View>
    </TouchableWithoutFeedback>
  );
}
