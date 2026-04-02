import { View, Text, TextInput, TouchableOpacity, Image, KeyboardAvoidingView, TouchableWithoutFeedback, Keyboard, Platform, ScrollView, Alert, ActivityIndicator } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

export default function SignupScreen() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [gender, setGender] = useState('');
  const [agreed, setAgreed] = useState(true);
  const [loading, setLoading] = useState(false);

  const handleSignup = async () => {
    if (!name || !email || !phone || !password) {
      Alert.alert('Incomplete Data', 'Please fill in all required fields.');
      return;
    }
    if (!agreed) {
      Alert.alert('Agreement Required', 'Please agree to the terms and conditions.');
      return;
    }

    try {
      setLoading(true);
      // Step 1: Request Signup
      const names = name.trim().split(' ');
      const firstName = names[0];
      const lastName = names.slice(1).join(' ') || 'User';

      const signupData = {
        first_name: firstName,
        last_name: lastName,
        email: email.trim(),
        phone: phone.trim(),
        password: password,
        role: 'rider',
      };

      await api.post('/users/register/request/', signupData);

      router.push({
        pathname: '/(auth)/otpverify',
        params: {
          value: email.trim(),
          type: 'signup',
          signupData: JSON.stringify(signupData),
        },
      });
    } catch (err: any) {
      console.error('Signup Request Failed:', err.response?.data || err.message);
      
      const data = err.response?.data;
      if (data) {
        if (data.phone) {
          Alert.alert(
            'Account Exists', 
            'This number is already registered.', 
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Go to Login', onPress: () => router.push('/(auth)/login') }
            ]
          );
          return;
        } else if (data.email) {
          Alert.alert('Email Taken', data.email[0]);
          return;
        } else if (data.detail) {
          Alert.alert('Signup Error', data.detail);
          return;
        } else if (data.non_field_errors) {
          Alert.alert('Signup Error', data.non_field_errors[0]);
          return;
        }
      }

      Alert.alert('Signup Error', 'Could not initiate signup. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 64, paddingBottom: 40 }} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">

          {/* Title */}
          <Text style={{ fontSize: 36, fontWeight: '800', color: Colors.textDark, marginBottom: 36 }}>Sign up</Text>

          {/* Name */}
          <View style={inputBox}>
            <TextInput value={name} onChangeText={setName} placeholder="Name" placeholderTextColor={Colors.textPlaceholder} style={{ flex: 1, fontSize: 16, color: Colors.textDark }} />
          </View>

          {/* Email */}
          <View style={[inputBox, { marginTop: 14 }]}>
            <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor={Colors.textPlaceholder} keyboardType="email-address" autoCapitalize="none" style={{ flex: 1, fontSize: 16, color: Colors.textDark }} />
          </View>

          {/* Phone */}
          <View style={[inputBox, { marginTop: 14 }]}>
            <TextInput value={phone} onChangeText={setPhone} placeholder="Phone Number" placeholderTextColor={Colors.textPlaceholder} keyboardType="phone-pad" style={{ flex: 1, fontSize: 16, color: Colors.textDark }} />
          </View>

          {/* Password */}
          <View style={[inputBox, { marginTop: 14 }]}>
            <TextInput value={password} onChangeText={setPassword} placeholder="Password" placeholderTextColor={Colors.textPlaceholder} secureTextEntry style={{ flex: 1, fontSize: 16, color: Colors.textDark }} />
          </View>

          {/* Gender */}
          <View style={[inputBox, { marginTop: 14 }]}>
            <TextInput value={gender} onChangeText={setGender} placeholder="Gender" placeholderTextColor={Colors.textPlaceholder} style={{ flex: 1, fontSize: 16, color: Colors.textDark }} />
          </View>

          {/* Terms checkbox */}
          <TouchableOpacity onPress={() => setAgreed(p => !p)} style={{ flexDirection: 'row', alignItems: 'flex-start', marginTop: 20, marginBottom: 24, gap: 10 }}>
            <Ionicons name={agreed ? 'checkmark-circle' : 'ellipse-outline'} size={24} color={agreed ? '#27AE60' : Colors.textPlaceholder} style={{ marginTop: 1 }} />
            <Text style={{ flex: 1, fontSize: 14, color: Colors.textDark, lineHeight: 22 }}>
              By signing up. you agree to the{' '}
              <Text style={{ color: Colors.primary, fontWeight: '600' }}>Terms of service</Text>
              {' '}and{' '}
              <Text style={{ color: Colors.primary, fontWeight: '600' }}>Privacy policy.</Text>
            </Text>
          </TouchableOpacity>

          {/* Sign Up button */}
          <TouchableOpacity
            onPress={handleSignup}
            disabled={loading}
            style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center', marginBottom: 28, opacity: loading ? 0.7 : 1 }}
          >
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Sign Up</Text>}
          </TouchableOpacity>

          {/* OR divider */}
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 28 }}>
            <View style={{ flex: 1, height: 1, backgroundColor: '#E0E0E0' }} />
            <Text style={{ marginHorizontal: 12, fontSize: 14, color: Colors.textMuted }}>or</Text>
            <View style={{ flex: 1, height: 1, backgroundColor: '#E0E0E0' }} />
          </View>

          {/* Social buttons */}
          <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 16, marginBottom: 36 }}>
            {/* Google */}
            <TouchableOpacity style={socialBtn}>
              <Image source={{ uri: 'https://www.google.com/favicon.ico' }} style={{ width: 28, height: 28 }} resizeMode="contain" />
            </TouchableOpacity>

            {/* Facebook */}
            <TouchableOpacity style={socialBtn}>
              <Image source={require('../../assets/images/facebook.jpg')} style={{ width: 28, height: 28 }} resizeMode="contain" />
            </TouchableOpacity>
          </View>

          {/* Sign In link */}
          <View style={{ flexDirection: 'row', justifyContent: 'center' }}>
            <Text style={{ fontSize: 16, color: Colors.textDark }}>Already have an account? </Text>
            <TouchableOpacity onPress={() => router.push('/(auth)/login')}>
              <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.primary }}>Sign in</Text>
            </TouchableOpacity>
          </View>

        </ScrollView>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}

const inputBox = {
  flexDirection: 'row' as const,
  alignItems: 'center' as const,
  borderWidth: 1.5,
  borderColor: '#D0D0D0',
  borderRadius: 10,
  paddingHorizontal: 16,
  paddingVertical: 14,
  backgroundColor: '#FFFFFF',
};

const socialBtn = {
  width: 60,
  height: 60,
  borderRadius: 16,
  borderWidth: 1.5,
  borderColor: '#E0E0E0',
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
  backgroundColor: '#FFFFFF',
};
