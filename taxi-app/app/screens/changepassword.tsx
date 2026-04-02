import { View, Text, TextInput, TouchableOpacity, Alert, TouchableWithoutFeedback, Keyboard } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';

export default function ChangePasswordScreen() {
  const router = useRouter();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);
  const { api } = require('../../services/api');

  const handleSave = async () => {
    if (!oldPassword || !newPassword || !confirmPassword) {
      Alert.alert('Error', 'Please fill in all fields.');
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert('Error', 'Passwords do not match.');
      return;
    }
    if (newPassword.length < 6) {
      Alert.alert('Error', 'New password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      await api.post('/users/change-password/', {
        old_password: oldPassword,
        new_password: newPassword,
      });
      Alert.alert('Success', 'Your password has been updated.');
      
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      router.back();
    } catch (error: any) {
      const msg = error.response?.data?.error || "Failed to update password.";
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    flexDirection: 'row' as const, alignItems: 'center' as const,
    borderWidth: 1, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 16, paddingVertical: 14,
    backgroundColor: Colors.white,
  };

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Change Password</Text>
      </View>

      <View style={{ paddingHorizontal: 16, paddingTop: 16, gap: 14 }}>
        {/* Old Password */}
        <View style={inputStyle}>
          <TextInput
            value={oldPassword}
            onChangeText={setOldPassword}
            placeholder="Old Password"
            placeholderTextColor={Colors.textMuted}
            secureTextEntry={!showOld}
            style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
          />
          <TouchableOpacity onPress={() => setShowOld(p => !p)}>
            <Ionicons name={showOld ? 'eye-outline' : 'eye-off-outline'} size={22} color={Colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* New Password */}
        <View style={inputStyle}>
          <TextInput
            value={newPassword}
            onChangeText={setNewPassword}
            placeholder="New Password"
            placeholderTextColor={Colors.textMuted}
            secureTextEntry={!showNew}
            style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
          />
          <TouchableOpacity onPress={() => setShowNew(p => !p)}>
            <Ionicons name={showNew ? 'eye-outline' : 'eye-off-outline'} size={22} color={Colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Confirm Password */}
        <View style={inputStyle}>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder="Confirm Password"
            placeholderTextColor={Colors.textMuted}
            secureTextEntry={!showConfirm}
            style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
          />
          <TouchableOpacity onPress={() => setShowConfirm(p => !p)}>
            <Ionicons name={showConfirm ? 'eye-outline' : 'eye-off-outline'} size={22} color={Colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Save button */}
        <TouchableOpacity
          onPress={handleSave}
          style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center', marginTop: 4 }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Save</Text>
        </TouchableOpacity>
      </View>
      </View>
    </TouchableWithoutFeedback>
  );
}
