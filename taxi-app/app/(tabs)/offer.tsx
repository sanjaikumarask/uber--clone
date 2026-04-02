import { View, Text, FlatList, TouchableOpacity, ActivityIndicator, RefreshControl, Alert } from 'react-native';
import React, { useState, useEffect } from 'react';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import Colors from '../../constants/Colors';
import OfferModal from '../../components/OfferModal';
import { api } from '../../services/api';

type Offer = {
  id: string;
  title: string;
  description: string;
  iconColorKey: keyof typeof Colors;
  code: string;
  tag?: string;
  terms: string[];  // non-optional to match OfferModal
};

export default function OfferScreen() {
  const [selected, setSelected] = useState<Offer | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchOffers = async () => {
    try {
      // FIXED: Correct endpoint is /offers/active/ not /offers/
      const res = await api.get('offers/active/');
      const rawData = res.data.results || res.data;
      
      const mappedOffers: Offer[] = rawData.map((item: any) => ({
        id: String(item.id),  // cast to string for type safety
        title: item.title,
        description: item.description || item.promo_description || '',
        iconColorKey: 'primary',
        code: item.code || item.promo_code || 'TRIPZO',
        tag: item.discount_value ? `${item.discount_value}${item.discount_type === 'percent' ? '%' : '₹'} OFF` : 'SPECIAL',
        terms: Array.isArray(item.terms) ? item.terms : []
      }));
      setOffers(mappedOffers);
    } catch (error: any) {
      console.error('[Offers] Fetch error:', error?.response?.data || error?.message);
      // Don't show alert if just empty — let empty state render
      if (error?.response?.status !== 404) {
        Alert.alert("Connection Error", "Failed to load active offers. Pull down to retry.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOffers();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchOffers();
  };

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, backgroundColor: '#F3F4F6', justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ marginTop: 12, color: Colors.textMuted }}>Checking for rewards...</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#F3F4F6' }}>
      {/* Header */}
      <View style={{ paddingTop: 20, paddingBottom: 12, alignItems: 'center', backgroundColor: Colors.white, borderBottomWidth: 1, borderBottomColor: '#EEE' }}>
        <Text style={{ fontSize: 24, fontWeight: '800', color: Colors.textDark, marginBottom: 12 }}>Special Offers</Text>
      </View>

      <FlatList
        data={offers}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 100, gap: 14 }}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 40 }}>
            <MaterialCommunityIcons name="ticket-percent-outline" size={64} color="#D1D5DB" />
            <Text style={{ marginTop: 16, fontSize: 16, color: Colors.textMuted }}>No active offers find right now.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() => setSelected(item)}
            activeOpacity={0.8}
            style={{ 
              flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.white, 
              borderRadius: 20, borderWidth: 1.5, borderColor: '#FDE68A', 
              paddingHorizontal: 16, paddingVertical: 18,
              shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2
            }}
          >
            <View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: '#FEF3C7', alignItems: 'center', justifyContent: 'center', marginRight: 16 }}>
              <MaterialCommunityIcons name="shopping" size={30} color={Colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <Text style={{ fontSize: 18, fontWeight: '800', color: Colors.textDark }}>{item.title}</Text>
                {item.tag && (
                  <View style={{ backgroundColor: '#FEF3C7', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 }}>
                    <Text style={{ fontSize: 10, fontWeight: '700', color: Colors.primary }}>{item.tag}</Text>
                  </View>
                )}
              </View>
              <Text numberOfLines={2} style={{ fontSize: 13, color: Colors.textMuted, lineHeight: 18 }}>{item.description}</Text>
            </View>
          </TouchableOpacity>
        )}
      />

      <OfferModal offer={selected as any} onClose={() => setSelected(null)} />
    </View>
  );
}
