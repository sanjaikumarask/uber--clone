import { View, Text, TextInput, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import SuccessModal from '../../components/SuccessModal';
import { api } from '../../services/api';

export default function ComplainScreen() {
  const router = useRouter();
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleSubmit = async () => {
    if (!subject.trim()) {
      Alert.alert('Error', 'Please enter a subject.');
      return;
    }
    if (message.trim().length < 10) {
      Alert.alert('Error', 'Complaint must be at least 10 characters.');
      return;
    }

    setLoading(true);
    try {
      await api.post('supports/tickets/general/', {
        category: 'driver_complaint', 
        subject: subject.trim(),
        description: message.trim(),
      });
      setShowSuccess(true);
      setSubject('');
      setMessage('');
    } catch (error: any) {
      console.error(error);
      Alert.alert('Submission Failed', error.response?.data?.error || 'Could not submit your complaint. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Complain</Text>
      </View>

      <View style={{ paddingHorizontal: 16, paddingTop: 16, gap: 16 }}>
        <TextInput
          value={subject}
          onChangeText={setSubject}
          placeholder="Vehicle not clean"
          placeholderTextColor={Colors.textMuted}
          style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 18, fontSize: 16, color: Colors.textDark, backgroundColor: '#FAFAFA' }}
        />
        <TextInput
          value={message}
          onChangeText={setMessage}
          placeholder="Write your complain here (minimum 10 characters)"
          placeholderTextColor={Colors.textMuted}
          multiline
          textAlignVertical="top"
          style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 18, fontSize: 16, color: Colors.textDark, backgroundColor: '#FAFAFA', height: 160 }}
        />
        <TouchableOpacity
          disabled={loading}
          onPress={handleSubmit}
          style={{ backgroundColor: loading ? Colors.textPlaceholder : Colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 4 }}
        >
          {loading ? (
            <ActivityIndicator color={Colors.white} />
          ) : (
            <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Submit Complaint</Text>
          )}
        </TouchableOpacity>
      </View>

      <SuccessModal
        visible={showSuccess}
        title="Sent Successfully"
        subtitle="Your complaint has been successfully recorded. We will contact you soon."
        buttonText="Back to Tripzo"
        onClose={() => { setShowSuccess(false); router.back(); }}
        onButton={() => { setShowSuccess(false); router.back(); }}
      />
    </View>
  );
}
