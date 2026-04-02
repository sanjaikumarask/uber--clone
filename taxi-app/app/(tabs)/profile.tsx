import { View, Text, TextInput, TouchableOpacity, Image, ScrollView, Alert, KeyboardAvoidingView, Platform, TouchableWithoutFeedback, Keyboard } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

const STORAGE_KEY = 'user_profile';

type Profile = {
  name: string;
  email: string;
  phone: string;
  gender: string;
  address: string;
};

const DEFAULT_PROFILE: Profile = {
  name: 'Wentrite',
  email: 'wentrite@email.com',
  phone: '',
  gender: '',
  address: '',
};

export default function ProfileScreen() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('users/me/');
        setProfile({
          name: `${res.data.first_name} ${res.data.last_name}`.trim(),
          email: res.data.email || '',
          phone: res.data.phone || '',
          gender: res.data.gender || '',
          address: res.data.address || '',
        });
      } catch (err) {
        console.error("Fetch profile error:", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleUpdate = async () => {
    const nameParts = profile.name.trim().split(' ');
    const first_name = nameParts[0];
    const last_name = nameParts.slice(1).join(' ');

    if (!first_name) {
      Alert.alert('Error', 'Name cannot be empty.');
      return;
    }

    try {
      setLoading(true);
      await api.patch('users/me/', {
        first_name,
        last_name,
        email: profile.email,
        phone: profile.phone,
        gender: profile.gender,
        address: profile.address,
      });
      Alert.alert('Success', 'Profile updated successfully.');
    } catch (err) {
      Alert.alert('Error', 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return null;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <View style={{ flex: 1 }}>
          {/* Header */}
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
            <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16 }}>
              <Ionicons name="chevron-back" size={24} color={Colors.textDark} />
            </TouchableOpacity>
            <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Edit Profile</Text>
          </View>

          <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 160 }} showsVerticalScrollIndicator={false}>

            {/* Profile image */}
            <View style={{ alignItems: 'center', marginTop: 16, marginBottom: 8 }}>
              <View style={{ width: 110, height: 110, borderRadius: 55, borderWidth: 3, borderColor: Colors.primary, overflow: 'hidden' }}>
                <Image
                  source={require('../../assets/images/profile.jpg')}
                  style={{ width: '100%', height: '100%' }}
                  resizeMode="cover"
                />
              </View>
            </View>

            {/* Display name */}
            <Text style={{ fontSize: 22, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 28 }}>
              {profile.name || 'Your Name'}
            </Text>

            {/* Name */}
            <Field label="Name">
              <TextInput
                value={profile.name}
                onChangeText={(v) => setProfile(p => ({ ...p, name: v }))}
                placeholder="Enter your name"
                placeholderTextColor={Colors.textPlaceholder}
                style={inputStyle}
              />
            </Field>

            {/* Email */}
            <Field label="Email">
              <TextInput
                value={profile.email}
                onChangeText={(v) => setProfile(p => ({ ...p, email: v }))}
                placeholder="Enter your email"
                placeholderTextColor={Colors.textPlaceholder}
                keyboardType="email-address"
                autoCapitalize="none"
                style={inputStyle}
              />
            </Field>

            {/* Phone */}
            <Field label="Phone Number">
              <TextInput
                value={profile.phone}
                onChangeText={(v) => setProfile(p => ({ ...p, phone: v }))}
                placeholder="Enter phone number"
                placeholderTextColor={Colors.textPlaceholder}
                keyboardType="phone-pad"
                style={inputStyle}
              />
            </Field>

            {/* Gender */}
            <Field label="Gender">
              <TextInput
                value={profile.gender}
                onChangeText={(v) => setProfile(p => ({ ...p, gender: v }))}
                placeholder="e.g. Male / Female"
                placeholderTextColor={Colors.textPlaceholder}
                style={inputStyle}
              />
            </Field>

            {/* Address */}
            <Field label="Address">
              <TextInput
                value={profile.address}
                onChangeText={(v) => setProfile(p => ({ ...p, address: v }))}
                placeholder="Enter your address"
                placeholderTextColor={Colors.textPlaceholder}
                style={inputStyle}
              />
            </Field>

            {/* Update button */}
            <TouchableOpacity
              onPress={handleUpdate}
              style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 8 }}
            >
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Update</Text>
            </TouchableOpacity>

          </ScrollView>
        </View>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={{ fontSize: 13, fontWeight: '600', color: Colors.textMuted, marginBottom: 6 }}>{label}</Text>
      {children}
    </View>
  );
}

const inputStyle = {
  borderWidth: 1,
  borderColor: '#E0E0E0',
  borderRadius: 12,
  paddingHorizontal: 16,
  paddingVertical: 14,
  fontSize: 15,
  color: Colors.textDark,
  backgroundColor: Colors.white,
};
