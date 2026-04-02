import { View, Text, TouchableOpacity, Alert } from 'react-native';
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function DeleteAccountScreen() {
  const router = useRouter();

  const handleDelete = () => {
    Alert.alert('Delete Account', 'Are you sure you want to permanently delete your account?', [
      { text: 'Cancel', style: 'cancel' },
      { 
        text: 'Delete', 
        style: 'destructive', 
        onPress: async () => {
          try {
            await api.delete('users/delete-account/');
            const { Storage } = require('../../services/storage');
            await Storage.clear();
            Alert.alert('Deleted', 'Your account has been deactivated.', [
              { text: 'OK', onPress: () => router.replace('/(auth)/welcome') }
            ]);
          } catch (err) {
            Alert.alert('Error', 'Failed to delete account.');
          }
        } 
      },
    ]);
  };

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Delete Account</Text>
      </View>

      <View style={{ paddingHorizontal: 16, paddingTop: 16, gap: 24 }}>
        <Text style={{ fontSize: 16, color: Colors.textDark, lineHeight: 22 }}>
          {'Are you sure you want to delete your account? Please read how account deletion will affect.\n'}
          {'Deleting your account removes personal information our database. Tour email becomes permanently reserved and same email cannot be re-use to register a new account.'}
        </Text>

        <TouchableOpacity
          onPress={handleDelete}
          style={{ backgroundColor: '#E53935', borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Delete</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
