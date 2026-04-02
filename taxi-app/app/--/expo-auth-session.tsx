import { useEffect, useState, useRef } from 'react';
import { View, Text, ActivityIndicator, Alert, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from '../../services/api';
import { Storage } from '../../services/storage';
import Colors from '../../constants/Colors';

export default function OAuthRedirectHandler() {
  const router = useRouter();
  const searchParams = useLocalSearchParams();
  const [status, setStatus] = useState('Securing Connection...');
  const [provider, setProvider] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorDetails, setErrorDetails] = useState<string | null>(null);
  
  // 🛡️ FIX 3: Race Condition Protector (Prevent Double Call)
  const processed = useRef(false);

  useEffect(() => {
    const keys = Object.keys(searchParams);
    
    // 🛡️ Guard 1: No params yet
    if (keys.length === 0) return;
    
    // 🛡️ Guard 2: Already locking/locked
    if (processed.current) return;
    
    // 🛡️ Guard 3: Already in-flight
    if (isProcessing) return;

    // 🔒 LOCK
    processed.current = true;
    
    handleOAuth();
  }, [searchParams]);

  async function handleOAuth() {
    setIsProcessing(true);
    setErrorDetails(null);
    
    try {
        console.log('[OAUTH_LOG] PARAMS RECEIVED:', JSON.stringify(searchParams, null, 2));

        // Detection Priority
        let extractedToken = searchParams.id_token || searchParams.access_token || searchParams.code;
        let detectedProvider = '';

        if (searchParams.id_token || (searchParams.access_token && searchParams.iss)) {
            detectedProvider = 'google';
        } else if (searchParams.access_token && searchParams.data_access_expiration_time) {
            detectedProvider = 'facebook';
        } else {
            detectedProvider = await AsyncStorage.getItem('pending_oauth_provider') || 'google';
        }

        setProvider(detectedProvider);
        setStatus(`Signing in with ${detectedProvider.charAt(0).toUpperCase() + detectedProvider.slice(1)}...`);

        if (!extractedToken) {
            throw new Error('No authentication token received from provider.');
        }

        // 🚀 API Call
        const res = await api.post('users/social-auth/', {
            provider: detectedProvider,
            token: extractedToken,
            state: searchParams.state
        });

        // Success Persistence
        const { access, refresh, user } = res.data;
        await Storage.setToken(access);
        await Storage.setRefreshToken(refresh);
        await Storage.setUserData(user);
        
        await AsyncStorage.removeItem('pending_oauth_provider');

        setStatus('Success! Welcome to Tripzo.');
        setTimeout(() => router.replace('/(tabs)'), 500);
        
    } catch (err: any) {
        // Unlock on definite failure to allow manual retry
        processed.current = false; 
        const message = err.response?.data?.error || err.response?.data?.detail || err.message;
        console.error('[OAUTH_ERROR] Exchange Failed:', message);
        setErrorDetails(message);
        setStatus('Authentication Failed');
    } finally {
        setIsProcessing(false);
    }
  }

  return (
    <View style={styles.container}>
      {(isProcessing || (Object.keys(searchParams).length > 0 && provider)) ? (
        <>
          <View style={styles.logoContainer}>
            {provider === 'google' ? (
              <Image source={{ uri: 'https://www.google.com/favicon.ico' }} style={styles.logo} resizeMode="contain" />
            ) : provider === 'facebook' ? (
              <Image source={require('../../assets/images/facebook.jpg')} style={styles.logo} resizeMode="contain" />
            ) : (
               <ActivityIndicator size="large" color={Colors.primary} />
            )}
          </View>
          <Text style={styles.title}>{status}</Text>
          <Text style={styles.subtitle}>Finalizing secure handshake...</Text>
        </>
      ) : errorDetails ? (
        <>
          <View style={styles.errorIcon}>
            <Text style={{ fontSize: 32 }}>⚠️</Text>
          </View>
          <Text style={styles.title}>{status}</Text>
          <Text style={styles.errorText}>{errorDetails}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => router.replace('/(auth)/login')}>
            <Text style={styles.retryBtnText}>Back to Login</Text>
          </TouchableOpacity>
        </>
      ) : (
        <ActivityIndicator size="large" color={Colors.primary} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f7f9fc', alignItems: 'center', justifyContent: 'center', padding: 40 },
  logoContainer: { width: 80, height: 80, borderRadius: 20, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', marginBottom: 20, elevation: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4 },
  logo: { width: 44, height: 44 },
  title: { marginTop: 10, fontSize: 18, fontWeight: '800', color: Colors.textDark, textAlign: 'center' },
  subtitle: { marginTop: 8, fontSize: 13, color: Colors.textMuted, textAlign: 'center' },
  errorText: { marginTop: 8, fontSize: 13, color: '#E53935', textAlign: 'center', marginBottom: 24 },
  errorIcon: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#FFEBEE', alignItems: 'center', justifyContent: 'center' },
  retryBtn: { backgroundColor: Colors.primary, paddingHorizontal: 28, paddingVertical: 12, borderRadius: 10 },
  retryBtnText: { color: '#fff', fontWeight: '700' }
});
