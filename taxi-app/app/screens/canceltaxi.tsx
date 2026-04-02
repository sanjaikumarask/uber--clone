import { View, Text, TouchableOpacity, TextInput, ScrollView, KeyboardAvoidingView, Modal } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

const REASONS = [
  'Waiting for long time',
  'Unable to contact driver',
  'Driver denied to go to destination',
  'Driver denied to come to pickup',
  'Wrong address shown',
  'The price is not reasonable',
];

export default function CancelTaxiScreen() {
  const router = useRouter();
  const [selected, setSelected] = useState<string>('Waiting for long time');
  const [other, setOther] = useState('');

  const [showCancelModal, setShowCancelModal] = useState(false);

  const handleSubmit = async () => {
    const reason = selected || (other.trim() ? other.trim() : null);
    if (!reason) return;
    
    try {
      // Get the current active ride ID from storage (should be set when booking)
      const rideId = await AsyncStorage.getItem('active_ride_id');
      if (rideId) {
        await api.post(`rides/${rideId}/cancel/`, { reason });
      }
      setShowCancelModal(true);
    } catch (err) {
      console.error("Cancel ride error:", err);
      // Even if API fails (e.g. ride already cancelled), we show the modal or an alert
      setShowCancelModal(true);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior="padding">
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: 20, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', position: 'absolute', left: 20 }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textDark} />
          <Text style={{ fontSize: 18, color: Colors.textDark, fontWeight: '500' }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ flex: 1, textAlign: 'center', fontSize: 20, fontWeight: '800', color: Colors.textDark }}>Cancel Taxi</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 120 }} showsVerticalScrollIndicator={false}>
        {/* Subtitle */}
        <Text style={{ fontSize: 15, color: Colors.textMuted, textAlign: 'center', marginBottom: 20, marginTop: 8 }}>
          Please select the reason of cancellation.
        </Text>

        {/* Reason list */}
        <View style={{ gap: 12 }}>
          {REASONS.map((reason) => {
            const isSelected = selected === reason;
            return (
              <TouchableOpacity
                key={reason}
                onPress={() => setSelected(reason)}
                style={{
                  flexDirection: 'row', alignItems: 'center',
                  borderWidth: 1.5,
                  borderColor: isSelected ? Colors.primary : '#D0D0D0',
                  borderRadius: 10, paddingHorizontal: 16, paddingVertical: 14,
                  backgroundColor: Colors.white,
                }}
              >
                {/* Checkbox */}
                <View style={{
                  width: 26, height: 26, borderRadius: 6, marginRight: 14,
                  backgroundColor: isSelected ? '#27AE60' : Colors.white,
                  borderWidth: isSelected ? 0 : 1.5,
                  borderColor: '#D0D0D0',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  {isSelected && <Ionicons name="checkmark" size={16} color="#fff" />}
                </View>
                <Text style={{ fontSize: 16, color: Colors.textDark }}>{reason}</Text>
              </TouchableOpacity>
            );
          })}

          {/* Other text input */}
          <TextInput
            value={other}
            onChangeText={(t) => { setOther(t); if (t) setSelected(''); }}
            placeholder="Other"
            placeholderTextColor={Colors.textPlaceholder}
            multiline
            textAlignVertical="top"
            style={{
              borderWidth: 1.5, borderColor: '#D0D0D0', borderRadius: 10,
              paddingHorizontal: 16, paddingVertical: 16,
              fontSize: 16, color: Colors.textDark,
              height: 120, marginTop: 4,
            }}
          />
        </View>
      </ScrollView>

      {/* Submit button */}
      <View style={{ position: 'absolute', bottom: 0, left: 0, right: 0, paddingHorizontal: 20, paddingBottom: 32, paddingTop: 12, backgroundColor: Colors.white }}>
        <TouchableOpacity
          onPress={handleSubmit}
          style={{ backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Submit</Text>
        </TouchableOpacity>
      </View>
      {/* Cancellation success modal */}
      <Modal visible={showCancelModal} transparent animationType="fade" onRequestClose={() => setShowCancelModal(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 }}>
          <View style={{ backgroundColor: Colors.white, borderRadius: 24, padding: 20, width: '100%', alignItems: 'center' }}>
            {/* Close */}
            <TouchableOpacity onPress={() => { setShowCancelModal(false); router.replace('/(tabs)'); }} style={{ position: 'absolute', top: 16, right: 16 }}>
              <Ionicons name="close" size={26} color={Colors.textDark} />
            </TouchableOpacity>

            {/* Emoji */}
            <Text style={{ fontSize: 60, marginTop: 8, marginBottom: 10 }}>😢</Text>

            {/* Title */}
            <Text style={{ fontSize: 20, fontWeight: '800', color: Colors.textDark, textAlign: 'center', marginBottom: 8 }}>
              We're so sad about{'\n'}your cancellation
            </Text>

            {/* Subtitle */}
            <Text style={{ fontSize: 13, color: Colors.textMuted, textAlign: 'center', lineHeight: 20, marginBottom: 16 }}>
              We will continue to improve our service & satify you on the next trip.
            </Text>

            {/* Back Home button */}
            <TouchableOpacity
              onPress={() => { setShowCancelModal(false); router.replace('/(tabs)'); }}
              style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center', width: '100%' }}
            >
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Back Home</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

    </KeyboardAvoidingView>
  );
}
