import { View, Text, TextInput, TouchableOpacity, Image, KeyboardAvoidingView, TouchableWithoutFeedback, Keyboard, Platform, ActivityIndicator, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useState, useEffect, useRef } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import * as Google from 'expo-auth-session/providers/google';
import * as Facebook from 'expo-auth-session/providers/facebook';
import * as AuthSession from 'expo-auth-session';
import * as Crypto from 'expo-crypto';
import Colors from '../../constants/Colors';
import SuccessModal from '../../components/SuccessModal';
import { api } from '../../services/api';
import { Storage } from '../../services/storage';

// FIXED: Essential for capturing the OAuth response after redirecting back to the app
WebBrowser.maybeCompleteAuthSession();

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 🛡️ THE PROXY GATEWAY: Essential for bypassing Google/Facebook scheme restrictions
  // Use separate endpoints to match specific provider console whitelists
  const googleProxyUrl = "https://overhelpfully-unerasing-brendon.ngrok-free.dev/api/users/google-proxy/";
  const fbProxyUrl = "https://overhelpfully-unerasing-brendon.ngrok-free.dev/api/users/facebook-proxy/";

  const [googleRequest, googleResponse, googlePromptAsync] = Google.useAuthRequest({
    // IMPORTANT: When using a web proxy (ngrok), we MUST use the Web Client ID 
    // because Native Android IDs do not support web-based Redirect URIs.
    clientId: "979130552711-9r2rqroaevvo28lk20mbs8i25crcbquu.apps.googleusercontent.com",
    // FIXED: Using dedicated Google Proxy URL
    redirectUri: googleProxyUrl,
    // 🛡️ SECURITY UPGRADE: Request BOTH access_token and id_token.
    // ID Tokens can be verified by the backend without a client secret.
    responseType: AuthSession.ResponseType.IdToken,
    scopes: ['openid', 'profile', 'email'],
    // 🔥 FIX: Force account selection screen
    prompt: AuthSession.Prompt.SelectAccount,
    extraParams: {
      prompt: 'select_account',
      nonce: 'nonce-' + Math.random().toString(36).substring(2),
    },

  });


  const [fbRequest, fbResponse, fbPromptAsync] = Facebook.useAuthRequest({
    clientId: "778299285076488",
    // FIXED: Using dedicated Facebook Proxy URL
    redirectUri: fbProxyUrl,
    // FIXED: Use Token response type
    responseType: AuthSession.ResponseType.Token,
  });

  // Social auth triggers only. Responses are handled in app/--/expo-auth-session.tsx
  const handleGoogleSocial = async () => {
    try {
      setLoading(true);
      await AsyncStorage.setItem('pending_oauth_provider', 'google');
      const result = await googlePromptAsync({ showInRecents: true });

      if (result?.type !== 'success') {
        setLoading(false);
      }
    } catch (e) {
      setLoading(false);
      Alert.alert('Error', 'Failed to start Google login');
    }
  };

  const handleFacebookSocial = async () => {
    try {
      setLoading(true);
      await AsyncStorage.setItem('pending_oauth_provider', 'facebook');
      const result = await fbPromptAsync();
      if (result?.type !== 'success') {
        setLoading(false);
      }
    } catch (e) {
      setLoading(false);
      Alert.alert('Error', 'Failed to start Facebook login');
    }
  };




  const handleLogin = async () => {
    if (!email || !password) {
      alert('Please enter both email/phone and password');
      return;
    }

    try {
      setLoading(true);
      const res = await api.post('users/login/', {
        phone: email,
        password: password,
      });

      const { access, refresh, user } = res.data;
      await Storage.setToken(access);
      await Storage.setRefreshToken(refresh);
      await Storage.setUserData(user);

      setShowSuccess(true);
      timerRef.current = setTimeout(() => {
        setShowSuccess(false);
        router.replace('/(tabs)');
      }, 2500);

    } catch (err: any) {
      console.error('Login Failed:', err.response?.data || err.message);
      
      if (!err.response) {
        Alert.alert('Login Error', 'No internet connection.');
      } else {
        const data = err.response.data;
        if (data) {
          if (data.non_field_errors) {
            const msg = data.non_field_errors[0].toLowerCase();
            if (msg.includes('invalid credentials')) {
              Alert.alert('Login Failed', 'Invalid email/phone or password. Please try again.');
            } else if (msg.includes('no_active_account') || msg.includes('no active account')) {
              Alert.alert('Login Failed', 'Account not found.');
            } else {
              Alert.alert('Login Failed', data.non_field_errors[0]);
            }
          } else if (data.detail) {
            const detailMsg = data.detail.toLowerCase();
            if (detailMsg.includes('unavailable')) {
              Alert.alert('Server Error', data.detail);
            } else if (detailMsg.includes('no active account') || detailMsg.includes('account not found')) {
              Alert.alert('Login Failed', 'Account not found.');
            } else {
              Alert.alert('Login Error', data.detail);
            }
          } else {
            Alert.alert('Login Error', 'Invalid credentials. Please try again.');
          }
        } else {
          Alert.alert('Login Error', 'Invalid credentials. Please try again.');
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return (
    <>
      <SuccessModal
        visible={showSuccess}
        title="Congratulations"
        subtitle="Your account is ready to use. You will be redirected to the Home Page in a few seconds."
        onClose={() => { setShowSuccess(false); router.replace('/(tabs)'); }}
      />

      <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <View style={{ flex: 1, paddingHorizontal: 24, paddingTop: 64 }}>

            {/* Title */}
            <Text style={{ fontSize: 36, fontWeight: '800', color: Colors.textDark, marginBottom: 36 }}>Log In</Text>

            {/* Email input */}
            <View style={inputBox}>
              <TextInput
                value={email}
                onChangeText={setEmail}
                placeholder="Email OR Phone Number"
                placeholderTextColor={Colors.textPlaceholder}
                keyboardType="email-address"
                autoCapitalize="none"
                style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
              />
            </View>

            {/* Password input */}
            <View style={[inputBox, { marginTop: 14 }]}>
              <TextInput
                value={password}
                onChangeText={setPassword}
                placeholder="Password"
                placeholderTextColor={Colors.textPlaceholder}
                secureTextEntry={!showPassword}
                style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
              />
              <TouchableOpacity onPress={() => setShowPassword(p => !p)}>
                <Ionicons name={showPassword ? 'eye-outline' : 'eye-off-outline'} size={22} color={Colors.textMuted} />
              </TouchableOpacity>
            </View>

            {/* Forget password */}
            <TouchableOpacity onPress={() => router.push('/(auth)/forgotpassword')} style={{ alignSelf: 'flex-end', marginTop: 10, marginBottom: 28 }}>
              <Text style={{ fontSize: 15, fontWeight: '600', color: '#E53935' }}>Forget password?</Text>
            </TouchableOpacity>

            {/* Log In button */}
            <TouchableOpacity
              onPress={handleLogin}
              disabled={loading}
              style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 18, alignItems: 'center', marginBottom: 28, opacity: loading ? 0.7 : 1 }}
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Log In</Text>}
            </TouchableOpacity>

            {/* OR divider */}
            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 28 }}>
              <View style={{ flex: 1, height: 1, backgroundColor: '#E0E0E0' }} />
              <Text style={{ marginHorizontal: 12, fontSize: 14, color: Colors.textMuted }}>or</Text>
              <View style={{ flex: 1, height: 1, backgroundColor: '#E0E0E0' }} />
            </View>

            {/* Social buttons */}
            <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 16, marginBottom: 36 }}>
              <TouchableOpacity 
                onPress={handleGoogleSocial} 
                disabled={loading || !googleRequest} 
                style={socialBtn}
              >
                <Image source={{ uri: 'https://www.google.com/favicon.ico' }} style={{ width: 28, height: 28 }} resizeMode="contain" />
              </TouchableOpacity>
              <TouchableOpacity 
                onPress={handleFacebookSocial} 
                disabled={loading || !fbRequest} 
                style={socialBtn}
              >
                <Image source={require('../../assets/images/facebook.jpg')} style={{ width: 28, height: 28 }} resizeMode="contain" />
              </TouchableOpacity>
            </View>

            {/* Sign Up link */}
            <View style={{ flexDirection: 'row', justifyContent: 'center' }}>
              <Text style={{ fontSize: 16, color: Colors.textDark }}>Don't have an account? </Text>
              <TouchableOpacity onPress={() => router.back()}>
                <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.primary }}>Sign Up</Text>
              </TouchableOpacity>
            </View>

          </View>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </>
  );
}

const inputBox = {
  flexDirection: 'row' as const,
  alignItems: 'center' as const,
  borderWidth: 1.5,
  borderColor: '#D0D0D0',
  borderRadius: 14,
  paddingHorizontal: 16,
  paddingVertical: 16,
  backgroundColor: '#FFFFFF',
};

const socialBtn = {
  width: 64,
  height: 64,
  borderRadius: 16,
  borderWidth: 1.5,
  borderColor: '#E0E0E0',
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
  backgroundColor: '#FFFFFF',
};
