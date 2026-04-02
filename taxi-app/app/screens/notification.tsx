import { View, Text, TouchableOpacity, SectionList, ActivityIndicator, RefreshControl, Alert } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

type NotifItem = { id: string | number; title: string; message: string; icon: string; created_at: string; is_read: boolean };
type NotifGroup = { title: string; data: NotifItem[] };

export default function NotificationScreen() {
  const router = useRouter();
  const [sections, setSections] = useState<NotifGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchNotifications = async () => {
    try {
      const res = await api.get('notifications/');
      const items: NotifItem[] = res.data.results || res.data;
      
      const grouped: { [key: string]: NotifItem[] } = {
        'Today': [],
        'Yesterday': [],
        'Earlier': []
      };

      const now = new Date();
      items.forEach(item => {
        const date = new Date(item.created_at);
        const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 3600 * 24));
        
        if (diffDays === 0) grouped['Today'].push(item);
        else if (diffDays === 1) grouped['Yesterday'].push(item);
        else grouped['Earlier'].push(item);
      });

      const finalSections = Object.keys(grouped)
        .filter(key => grouped[key].length > 0)
        .map(key => ({ title: key, data: grouped[key] }));

      setSections(finalSections);
    } catch (error) {
      console.error(error);
      Alert.alert("Error", "Could not load notifications.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchNotifications();
  };

  const handleMarkAsRead = async (id: string | number) => {
    // Optimistically update local state
    setSections(prev => prev.map(section => ({
      ...section,
      data: section.data.map(item => item.id === id ? { ...item, is_read: true } : item)
    })));

    try {
      // FIXED: Use the POST /mark-read/ custom action — PATCH is not allowed on ReadOnlyModelViewSet
      await api.post(`notifications/${id}/mark-read/`, {});
    } catch (e) {
      console.warn("Failed to mark as read", e);
    }
  };

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, backgroundColor: '#F5F5F5', justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#F5F5F5' }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12, backgroundColor: Colors.white }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid, marginLeft: 2 }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Notifications</Text>
      </View>

      <SectionList
        sections={sections}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 8, paddingBottom: 100 }}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        stickySectionHeadersEnabled={false}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 60 }}>
            <Ionicons name="notifications-off-outline" size={64} color="#D1D5DB" />
            <Text style={{ marginTop: 16, fontSize: 16, color: Colors.textMuted }}>No notifications yet.</Text>
          </View>
        }
        renderSectionHeader={({ section }) => (
          <Text style={{ fontSize: 16, fontWeight: '700', marginTop: 20, marginBottom: 12, color: Colors.textDark }}>
            {section.title}
          </Text>
        )}
        renderItem={({ item }) => (
          <TouchableOpacity 
            activeOpacity={0.7}
            onPress={() => handleMarkAsRead(item.id)}
            style={{ 
              flexDirection: 'row', alignItems: 'center', padding: 16, marginBottom: 12, 
              backgroundColor: Colors.white, borderRadius: 16,
              opacity: item.is_read ? 0.7 : 1,
              borderLeftWidth: item.is_read ? 0 : 4,
              borderLeftColor: Colors.primary
            }}
          >
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: '#F3F4F6', alignItems: 'center', justifyContent: 'center', marginRight: 14 }}>
              <Ionicons name={(item.icon || 'notifications') as any} size={24} color={Colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.textDark, marginBottom: 4 }}>{item.title}</Text>
              <Text style={{ fontSize: 14, color: Colors.textMuted, lineHeight: 20 }}>{item.message}</Text>
            </View>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}
