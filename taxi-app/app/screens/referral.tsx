import { View, Text, TouchableOpacity, Alert, Share, FlatList, ActivityIndicator, RefreshControl } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Clipboard from 'expo-clipboard';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

type Referral = { name: string; joined_date: string; status: string; reward: number };
type ReferralData = { total_referrals: number; earned_amount: number; pending_amount: number; referrals: Referral[] };

export default function ReferralScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [referralCode, setReferralCode] = useState('LOADING');
  const [stats, setStats] = useState<ReferralData | null>(null);

  const fetchData = async () => {
    try {
      // 1. Fetch Profile for Referral Code
      const profileRes = await api.get('users/me/');
      setReferralCode(profileRes.data.referral_code || 'TRIPZO-REF');

      // 2. Fetch Referral Stats
      const statsRes = await api.get('/incentives/referrals/');
      setStats(statsRes.data);
    } catch (error: any) {
      console.log('Referral fetch error:', error.response?.data || error.message);
      Alert.alert('Error', 'Could not load your referral data at this time.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleCopy = async () => {
    await Clipboard.setStringAsync(referralCode);
    Alert.alert('Copied!', `Referral code "${referralCode}" copied to clipboard.`);
  };

  const handleInvite = async () => {
    try {
      await Share.share({
        message: `Use my code ${referralCode} on Tripzo and get ₹50 off your first ride! Download now.`,
      });
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.white, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ marginTop: 12, color: Colors.textMuted }}>Loading incentives...</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Refer & Earn</Text>
      </View>

      <FlatList
        data={stats?.referrals || []}
        keyExtractor={(_, index) => index.toString()}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
        initialNumToRender={10}
        ListHeaderComponent={
          <View style={{ gap: 12, marginBottom: 24, paddingTop: 16 }}>
            <View style={{ backgroundColor: '#F3F4F6', borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 8 }}>
              <Text style={{ fontSize: 15, color: Colors.textMuted, marginBottom: 8 }}>Total Earned</Text>
              <Text style={{ fontSize: 36, fontWeight: '800', color: Colors.primary }}>₹{stats?.earned_amount || 0}</Text>
              <Text style={{ fontSize: 14, color: Colors.textDark, marginTop: 4 }}>
                {stats?.total_referrals || 0} Successful Referrals
              </Text>
            </View>

            <Text style={{ fontSize: 16, color: Colors.textDark, fontWeight: '600', marginBottom: 4 }}>
              Your Invite Code
            </Text>

            {/* Referral code row */}
            <View style={{ flexDirection: 'row', alignItems: 'center', borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 18, backgroundColor: Colors.white }}>
              <Text style={{ flex: 1, fontSize: 18, fontWeight: '700', color: Colors.textDark, letterSpacing: 2 }}>
                {referralCode}
              </Text>
              <TouchableOpacity onPress={handleCopy} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Ionicons name="copy-outline" size={24} color={Colors.primary} />
              </TouchableOpacity>
            </View>

            {/* Invite button */}
            <TouchableOpacity onPress={handleInvite} style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 8 }}>
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Share to Friends</Text>
            </TouchableOpacity>

            <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, marginTop: 24, paddingBottom: 8 }}>
              My Referrals
            </Text>
          </View>
        }
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 40, paddingHorizontal: 20 }}>
            <Ionicons name="people-outline" size={64} color="#E0E0E0" />
            <Text style={{ textAlign: 'center', marginTop: 12, color: Colors.textMuted, fontSize: 16 }}>
              You haven't referred anyone yet. Share your code to start earning!
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={{ flexDirection: 'row', alignItems: 'center', borderRadius: 16, padding: 16, marginBottom: 12, backgroundColor: Colors.white, borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.textDark }}>{item.name || 'Anonymous User'}</Text>
              <Text style={{ fontSize: 13, color: Colors.textMuted, marginTop: 2 }}>{new Date(item.joined_date).toLocaleDateString()}</Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={{ fontSize: 16, fontWeight: '800', color: item.status === 'completed' ? Colors.creditText : '#FF9800' }}>
                ₹{item.reward}
              </Text>
              <Text style={{ fontSize: 12, color: item.status === 'completed' ? Colors.creditText : '#FF9800', marginTop: 2, textTransform: 'capitalize' }}>
                {item.status}
              </Text>
            </View>
          </View>
        )}
      />
    </View>
  );
}
