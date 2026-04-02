import { View, Text, TouchableOpacity, Alert, Switch, ScrollView, ActivityIndicator, Modal, Platform } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import { Storage } from '../../services/storage';

export default function SettingsScreen() {
  const router = useRouter();
  
  // Profile State
  const [profile, setProfile] = useState<{ first_name: string; phone_number: string } | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  // Push Notifications State
  const [pushEnabled, setPushEnabled] = useState(false);
  const [loadingPush, setLoadingPush] = useState(false);

  // Legal Pages State
  const [legalModalVisible, setLegalModalVisible] = useState(false);
  const [legalTitle, setLegalTitle] = useState('');
  const [legalContent, setLegalContent] = useState('');
  const [loadingLegal, setLoadingLegal] = useState(false);
  
  // Language State
  const [languageModalVisible, setLanguageModalVisible] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('English');

  useEffect(() => {
    fetchProfile();
    loadPreferences();
    checkPushStatus();
  }, []);

  const loadPreferences = async () => {
    try {
      const lang = await AsyncStorage.getItem('@Tripzo:selected_language');
      if (lang) setSelectedLanguage(lang);
    } catch (e) {}
  };

  const fetchProfile = async () => {
    try {
      const res = await api.get('users/me/');
      setProfile(res.data);
    } catch (e) {
      console.log('Profile fetch err', e);
    } finally {
      setLoadingProfile(false);
    }
  };

  const checkPushStatus = async () => {
    try {
      if (Platform.OS === 'web') return; // SecureStore doesn't work on Web
      const status = await SecureStore.getItemAsync('push_enabled');
      setPushEnabled(status === 'true');
    } catch (e) {}
  };

  const handleTogglePush = async (value: boolean) => {
    if (Platform.OS === 'web') {
      Alert.alert('Not Supported', 'Push notifications are not supported on the web.');
      return;
    }

    setLoadingPush(true);
    try {
      if (value) {
        if (!Device.isDevice) {
          Alert.alert('Error', 'Must use physical device for Push Notifications');
          setLoadingPush(false);
          return;
        }

        let Notifications;
        try {
          Notifications = await import('expo-notifications');
        } catch (e) {
          Alert.alert('Not Supported', 'Android Push notifications functionality was removed from Expo Go in SDK 53.');
          setPushEnabled(false);
          setLoadingPush(false);
          return;
        }

        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }
        if (finalStatus !== 'granted') {
          Alert.alert('Permission Denied', 'Please enable notifications in your phone settings.');
          setPushEnabled(false);
          return;
        }
        
        // Get Token
        const tokenData = await Notifications.getExpoPushTokenAsync({ projectId: 'your-project-id' }); // Note: Need projectId in real app or via Constants
        const token = tokenData.data;

        // Save to backend
        await api.post('/notifications/token/', { token, device_type: Platform.OS });
        await SecureStore.setItemAsync('push_enabled', 'true');
        await SecureStore.setItemAsync('push_token_val', token);
        setPushEnabled(true);
      } else {
        // Disable
        const savedToken = await SecureStore.getItemAsync('push_token_val');
        if (savedToken) {
          await api.delete('/notifications/token/', { data: { token: savedToken } });
        }
        await SecureStore.deleteItemAsync('push_enabled');
        await SecureStore.deleteItemAsync('push_token_val');
        setPushEnabled(false);
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.error || 'Failed to update push notification preferences.');
      setPushEnabled(!value); // Revert UI
    } finally {
      setLoadingPush(false);
    }
  };

  const fetchLegalContent = async (type: 'about' | 'privacy', title: string) => {
    setLegalTitle(title);
    setLegalModalVisible(true);
    setLoadingLegal(true);
    setLegalContent('');

    const cacheKey = `@Tripzo:legal_${type}`;
    
    try {
      // 1. Show cached version immediately if available
      const cached = await AsyncStorage.getItem(cacheKey);
      if (cached) setLegalContent(cached);

      // 2. Fetch fresh from API using specialized slug patterns
      const slug = type === 'about' ? 'about_us' : 'privacy_policy';
      const res = await api.get(`users/content/${slug}/`);
      
      const freshContent = res.data.content || "No content available.";
      
      setLegalContent(freshContent);
      await AsyncStorage.setItem(cacheKey, freshContent); // Update cache
    } catch (error) {
      if (!legalContent) setLegalContent("Failed to load content. Please check your internet connection and try again.");
    } finally {
      setLoadingLegal(false);
    }
  };

  const handleLanguageChange = async (lang: string) => {
    setSelectedLanguage(lang);
    setLanguageModalVisible(false);
    try {
      await AsyncStorage.setItem('@Tripzo:selected_language', lang);
    } catch (e) {}
  };

  const handleLogout = async () => {
    Alert.alert(
      "Logout",
      "Are you sure you want to log out of Tripzo?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Logout", 
          style: "destructive",
          onPress: async () => {
            try {
              // Clear Push Token from backend if enabled
              const savedToken = await SecureStore.getItemAsync('push_token_val');
              if (savedToken) await api.delete('/notifications/token/', { data: { token: savedToken } }).catch(() => {});
              
              // Wipe local Keystore / AsyncStorage
              await Storage.clear();
              // Redirect to Auth Stack
              router.replace('/(auth)/login');
            } catch (e) {
              Alert.alert('Error', 'Failed to logout cleanly.');
            }
          }
        }
      ]
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#F8F9FA' }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 16, backgroundColor: Colors.white }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Settings</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        
        {/* Profile Section */}
        <View style={{ backgroundColor: Colors.white, paddingHorizontal: 20, paddingVertical: 24, marginBottom: 12, alignItems: 'center' }}>
          <View style={{ width: 80, height: 80, borderRadius: 40, backgroundColor: Colors.primaryLight, alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Ionicons name="person" size={36} color={Colors.primary} />
          </View>
          {loadingProfile ? (
            <ActivityIndicator color={Colors.primary} />
          ) : (
            <>
              <Text style={{ fontSize: 22, fontWeight: '800', color: Colors.textDark }}>{profile?.first_name || 'Tripzo Rider'}</Text>
              <Text style={{ fontSize: 15, color: Colors.textMuted, marginTop: 4 }}>{profile?.phone_number || '+91 •••••••••'}</Text>
            </>
          )}
        </View>

        {/* Preferences */}
        <Text style={{ fontSize: 14, fontWeight: '700', color: Colors.textMuted, marginLeft: 20, marginBottom: 8, marginTop: 12, textTransform: 'uppercase' }}>Preferences</Text>
        <View style={{ backgroundColor: Colors.white, paddingHorizontal: 20, paddingVertical: 8, borderTopWidth: 1, borderBottomWidth: 1, borderColor: '#F0F0F0' }}>
          
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: '#E1F5FE', alignItems: 'center', justifyContent: 'center', marginRight: 12 }}>
                <Ionicons name="notifications" size={18} color="#03A9F4" />
              </View>
              <Text style={{ fontSize: 16, color: Colors.textDark, fontWeight: '500' }}>Push Notifications</Text>
            </View>
            {loadingPush ? <ActivityIndicator size="small" color={Colors.primary} /> : (
              <Switch 
                value={pushEnabled} 
                onValueChange={handleTogglePush} 
                trackColor={{ false: '#E0E0E0', true: Colors.primary }}
                thumbColor={Colors.white}
              />
            )}
          </View>

          <TouchableOpacity 
            onPress={() => setLanguageModalVisible(true)}
            style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12 }}
          >
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: '#E8F5E9', alignItems: 'center', justifyContent: 'center', marginRight: 12 }}>
                <Ionicons name="language" size={18} color="#4CAF50" />
              </View>
              <Text style={{ fontSize: 16, color: Colors.textDark, fontWeight: '500' }}>Language</Text>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Text style={{ fontSize: 14, color: Colors.textMuted, marginRight: 8 }}>{selectedLanguage}</Text>
              <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
            </View>
          </TouchableOpacity>

        </View>

        {/* Legal & Support */}
        <Text style={{ fontSize: 14, fontWeight: '700', color: Colors.textMuted, marginLeft: 20, marginBottom: 8, marginTop: 24, textTransform: 'uppercase' }}>Legal & Support</Text>
        <View style={{ backgroundColor: Colors.white, paddingHorizontal: 20, paddingVertical: 8, borderTopWidth: 1, borderBottomWidth: 1, borderColor: '#F0F0F0' }}>
          
          <TouchableOpacity onPress={() => fetchLegalContent('about', 'About Us')} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons name="information-circle-outline" size={22} color={Colors.textMid} style={{ marginRight: 12 }} />
              <Text style={{ fontSize: 16, color: Colors.textDark }}>About Us</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity onPress={() => fetchLegalContent('privacy', 'Privacy Policy')} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons name="shield-checkmark-outline" size={22} color={Colors.textMid} style={{ marginRight: 12 }} />
              <Text style={{ fontSize: 16, color: Colors.textDark }}>Privacy Policy</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.push('/screens/helpsupport')} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons name="help-buoy-outline" size={22} color={Colors.textMid} style={{ marginRight: 12 }} />
              <Text style={{ fontSize: 16, color: Colors.textDark }}>Help Center</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
          </TouchableOpacity>

        </View>

        {/* Account Actions */}
        <View style={{ marginTop: 32, paddingHorizontal: 20 }}>
          <TouchableOpacity onPress={handleLogout} style={{ backgroundColor: Colors.white, borderRadius: 12, paddingVertical: 16, alignItems: 'center', borderWidth: 1.5, borderColor: '#FFEbee', flexDirection: 'row', justifyContent: 'center' }}>
            <Ionicons name="log-out-outline" size={20} color="#F44336" style={{ marginRight: 8 }} />
            <Text style={{ fontSize: 16, fontWeight: '700', color: '#F44336' }}>Log Out</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>

      {/* Legal Content Modal */}
      <Modal visible={legalModalVisible} animationType="slide" presentationStyle="pageSheet" onRequestClose={() => setLegalModalVisible(false)}>
        <View style={{ flex: 1, backgroundColor: Colors.white }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' }}>
            <TouchableOpacity onPress={() => setLegalModalVisible(false)} style={{ padding: 4 }}>
              <Ionicons name="close" size={24} color={Colors.textDark} />
            </TouchableOpacity>
            <Text style={{ flex: 1, textAlign: 'center', fontSize: 18, fontWeight: '700', color: Colors.textDark, marginRight: 32 }}>{legalTitle}</Text>
          </View>
          <ScrollView contentContainerStyle={{ padding: 20 }}>
            {loadingLegal && !legalContent ? (
              <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
            ) : (
              <Text style={{ fontSize: 15, lineHeight: 24, color: Colors.textDark }}>{legalContent}</Text>
            )}
          </ScrollView>
        </View>
      </Modal>

      {/* Language Modal */}
      <Modal visible={languageModalVisible} animationType="slide" transparent={true} onRequestClose={() => setLanguageModalVisible(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
          <View style={{ backgroundColor: Colors.white, borderTopLeftRadius: 32, borderTopRightRadius: 32, padding: 24, paddingBottom: Platform.OS === 'ios' ? 40 : 24 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <Text style={{ fontSize: 20, fontWeight: '800', color: Colors.textDark }}>Choose Language</Text>
              <TouchableOpacity onPress={() => setLanguageModalVisible(false)} style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: '#F0F0F0', alignItems: 'center', justifyContent: 'center' }}>
                <Ionicons name="close" size={20} color={Colors.textDark} />
              </TouchableOpacity>
            </View>
            
            {['English', 'Tamil', 'Hindi', 'Spanish'].map((lang) => (
              <TouchableOpacity 
                key={lang} 
                onPress={() => handleLanguageChange(lang)}
                style={{ 
                  flexDirection: 'row', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                  paddingVertical: 16, 
                  borderBottomWidth: 1, 
                  borderBottomColor: '#F0F0F0'
                }}
              >
                <Text style={{ fontSize: 17, color: selectedLanguage === lang ? Colors.primary : Colors.textDark, fontWeight: selectedLanguage === lang ? '700' : '500' }}>{lang}</Text>
                {selectedLanguage === lang && <Ionicons name="checkmark-circle" size={24} color={Colors.primary} />}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>

    </View>
  );
}
