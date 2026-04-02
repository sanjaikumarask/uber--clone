import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import { ActivityIndicator } from 'react-native';

export default function AboutUsScreen() {
  const router = useRouter();
  const [data, setData] = useState<{ title: string, content: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('users/content/about_us/');
        setData(res.data);
      } catch (err) {
        console.error("Fetch about us error:", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>About Us</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        {loading ? (
          <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
        ) : data ? (
          <>
            <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, marginBottom: 14 }}>
              {data.title}
            </Text>
            <Text style={{ fontSize: 14, color: Colors.textDark, lineHeight: 24, textAlign: 'justify' }}>
              {data.content}
            </Text>
          </>
        ) : (
          <Text style={{ fontSize: 14, color: Colors.textMuted }}>No content available.</Text>
        )}
      </ScrollView>
    </View>
  );
}
