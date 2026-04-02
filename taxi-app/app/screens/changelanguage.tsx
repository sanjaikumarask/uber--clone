import { View, Text, TouchableOpacity, FlatList, Alert } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';

const LANGUAGES = [
  { code: 'en', name: 'English',    native: 'English',    flag: '🇺🇸' },
  { code: 'hi', name: 'Hindi',      native: 'Hindi',      flag: '🇮🇳' },
  { code: 'ar', name: 'Arabic',     native: 'Arabic',     flag: '🇵🇸' },
  { code: 'fr', name: 'French',     native: 'French',     flag: '🇫🇷' },
  { code: 'de', name: 'German',     native: 'German',     flag: '🇩🇪' },
  { code: 'pt', name: 'Portuguese', native: 'Portuguese', flag: '🇵🇹' },
  { code: 'tr', name: 'Turkish',    native: 'Turkish',    flag: '🇹🇷' },
  { code: 'nl', name: 'Dutch',      native: 'Nederlands', flag: '🇳🇱' },
];

export default function ChangeLanguageScreen() {
  const router = useRouter();
  const [selected, setSelected] = useState('en');

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Change Language</Text>
      </View>

      <FlatList
        data={LANGUAGES}
        keyExtractor={(item) => item.code}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 120, gap: 12 }}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => {
          const isSelected = selected === item.code;
          return (
            <TouchableOpacity
              onPress={() => setSelected(item.code)}
              style={{
                flexDirection: 'row', alignItems: 'center',
                borderWidth: 1.5,
                borderColor: isSelected ? Colors.primary : '#E0E0E0',
                borderRadius: 14, paddingHorizontal: 14, paddingVertical: 12,
                backgroundColor: Colors.white,
              }}
            >
              {/* Flag */}
              <Text style={{ fontSize: 40, marginRight: 14 }}>{item.flag}</Text>

              {/* Name */}
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 16, fontWeight: '600', color: Colors.textDark }}>{item.name}</Text>
                <Text style={{ fontSize: 13, color: Colors.textMuted, marginTop: 2 }}>{item.native}</Text>
              </View>

              {/* Check icon */}
              <Ionicons
                name="checkmark-circle"
                size={26}
                color={isSelected ? Colors.primary : '#D0D0D0'}
              />
            </TouchableOpacity>
          );
        }}
      />

      {/* Save button */}
      <View style={{ position: 'absolute', bottom: 0, left: 0, right: 0, paddingHorizontal: 16, paddingBottom: 32, paddingTop: 12, backgroundColor: Colors.white }}>
        <TouchableOpacity
          onPress={() => Alert.alert('Saved', `Language changed to ${LANGUAGES.find(l => l.code === selected)?.name}.`)}
          style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}
        >
          <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Save</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
