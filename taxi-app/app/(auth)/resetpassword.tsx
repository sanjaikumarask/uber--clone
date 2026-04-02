import { View, Text, TextInput, TouchableOpacity, Alert, KeyboardAvoidingView, TouchableWithoutFeedback, Keyboard, ActivityIndicator } from 'react-native';
import React, { useState } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

export default function ResetPasswordScreen() {
  const router = useRouter();
  const { value, otp } = useLocalSearchParams<{ value: string; otp: string }>();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (!newPassword || !confirmPassword) {
      Alert.alert('Please fill in all fields.');
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert('Passwords do not match.');
      return;
    }

    try {
      setLoading(true);
      await api.post('/users/reset-password/', {
        phone: value,
        otp: otp,
        password: newPassword,
      });

      Alert.alert('Success', 'Password updated successfully.', [
        { text: 'OK', onPress: () => router.replace('/(auth)/login') },
      ]);
    } catch (err: any) {
      console.error('Reset PW Error:', err.response?.data || err.message);
      Alert.alert('Reset Failed', 'Incorrect OTP or session expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior="padding">
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <View style={{ flex: 1, paddingHorizontal: 24, paddingTop: 64 }}>

          {/* Title */}
          <Text style={{ fontSize: 30, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 10 }}>
            Set New password
          </Text>
          <Text style={{ fontSize: 15, color: Colors.textMuted, textAlign: 'center', marginBottom: 40 }}>
            Set your new password
          </Text>

          {/* New Password */}
          <View style={inputBox}>
            <TextInput
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder="Enter Your New Password"
              placeholderTextColor={Colors.textPlaceholder}
              secureTextEntry={!showNew}
              style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
            />
            <TouchableOpacity onPress={() => setShowNew(p => !p)}>
              <Ionicons name={showNew ? 'eye-outline' : 'eye-off-outline'} size={22} color={Colors.textMuted} />
            </TouchableOpacity>
          </View>

          {/* Confirm Password */}
          <View style={[inputBox, { marginTop: 14 }]}>
            <TextInput
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              placeholder="Confirm Password"
              placeholderTextColor={Colors.textPlaceholder}
              secureTextEntry={!showConfirm}
              style={{ flex: 1, fontSize: 16, color: Colors.textDark }}
            />
            <TouchableOpacity onPress={() => setShowConfirm(p => !p)}>
              <Ionicons name={showConfirm ? 'eye-outline' : 'eye-off-outline'} size={22} color={Colors.textMuted} />
            </TouchableOpacity>
          </View>

          {/* Hint */}
          <Text style={{ fontSize: 13, color: Colors.textMuted, marginTop: 10 }}>
            Atleast 1 number or a special character
          </Text>

          {/* Save button */}
          <View style={{ position: 'absolute', bottom: 32, left: 24, right: 24 }}>
            <TouchableOpacity
              onPress={handleSave}
              style={{ backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
            >
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Save</Text>
            </TouchableOpacity>
          </View>

        </View>
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
