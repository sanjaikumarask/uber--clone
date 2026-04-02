import { View, Text, TouchableOpacity, FlatList } from 'react-native';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import { ActivityIndicator, RefreshControl } from 'react-native';

type Tab = 'upcoming' | 'completed' | 'cancelled';



const TABS: { key: Tab; label: string }[] = [
  { key: 'upcoming',  label: 'Upcoming'  },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
];

export default function HistoryScreen() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>('upcoming');
  const [rides, setRides] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const res = await api.get('rides/history/');
      setRides(res.data);
    } catch (err) {
      console.error("Fetch history error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchHistory();
  };

  const filteredData = rides.filter(ride => {
    if (activeTab === 'upcoming') return ['REQUESTED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP'].includes(ride.status);
    if (activeTab === 'completed') return ride.status === 'COMPLETED';
    if (activeTab === 'cancelled') return ride.status === 'CANCELLED';
    return false;
  });

  const renderRight = (item: any) => {
    if (activeTab === 'upcoming')
      return <Text style={{ fontSize: 14, fontWeight: '600', color: Colors.textDark }}>{item.time}</Text>;
    if (activeTab === 'completed')
      return <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.creditText }}>Done</Text>;
    return <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.debitText }}>Cancel</Text>;
  };

  return (
    <View className="flex-1" style={{ backgroundColor: Colors.white }}>
      {/* Header */}
      <View className="flex-row items-center justify-center px-4 pt-4 pb-3">
        <TouchableOpacity className="absolute left-4 flex-row items-center" onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text className="text-base ml-0.5" style={{ color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text className="text-xl font-bold" style={{ color: Colors.textDark }}>History</Text>
      </View>

      {/* Tab switcher */}
      <View className="mx-4 mt-2 mb-5 flex-row rounded-2xl overflow-hidden" style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder, backgroundColor: Colors.primaryBg }}>
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            onPress={() => setActiveTab(tab.key)}
            className="flex-1 py-2.5 items-center justify-center"
            style={{
              backgroundColor: activeTab === tab.key ? Colors.primary : 'transparent',
              borderRadius: activeTab === tab.key ? 14 : 0,
              margin: activeTab === tab.key ? 3 : 0,
            }}
          >
            <Text
              className="text-base font-semibold"
              style={{ color: activeTab === tab.key ? Colors.white : Colors.textMuted }}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* List */}
      {loading && !refreshing ? (
        <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={filteredData}
          keyExtractor={(item: any) => item.id.toString()}
          initialNumToRender={10}
          maxToRenderPerBatch={10}
          windowSize={5}
          getItemLayout={(_data: any, index: number) => ({ length: 90, offset: 90 * index, index })}
          contentContainerStyle={{ paddingHorizontal: 16, gap: 12, paddingBottom: 40 }}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={
            <Text style={{ textAlign: 'center', marginTop: 40, color: Colors.textMuted }}>No rides found</Text>
          }
          ListFooterComponent={
            <View style={{ paddingVertical: 20 }}>
              {filteredData.length > 0 && <Text style={{ textAlign: 'center', color: Colors.textPlaceholder, fontSize: 13 }}>End of history</Text>}
            </View>
          }
          renderItem={({ item }: { item: any }) => (
            <View
              className="flex-row items-center px-4 py-4 rounded-2xl"
              style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder, backgroundColor: Colors.white }}
            >
              <View className="flex-1">
                <Text className="text-base font-bold mb-1" style={{ color: Colors.textDark }}>
                  {item.pickup_address?.split(',')[0] || 'Ride'}
                </Text>
                <Text className="text-sm" style={{ color: Colors.textMuted }}>
                  {item.driver?.first_name ? `${item.driver.first_name} • ${item.vehicle_type}` : 'Searching for driver...'}
                </Text>
              </View>
              {renderRight(item)}
            </View>
          )}
        />
      )}
    </View>
  );
}
