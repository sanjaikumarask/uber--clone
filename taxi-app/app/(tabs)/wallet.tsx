import { View, Text, TouchableOpacity, FlatList, ActivityIndicator, Alert } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import Sidebar from '../../components/Sidebar';
import { api } from '../../services/api';

type Transaction = { id: string; name: string; time: string; amount: number; type: 'debit' | 'credit' };

export default function WalletScreen() {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  const [availableBalance, setAvailableBalance] = useState<number>(0);
  const [heldBalance, setHeldBalance] = useState<number>(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchWalletData();
  }, []);

  const fetchWalletData = async () => {
    setLoading(true);
    try {
      // Fetch live wallet balances from ledger
      const balanceRes = await api.get('/payments/wallet/');
      setAvailableBalance(parseFloat(balanceRes.data.available_balance) || 0);
      setHeldBalance(parseFloat(balanceRes.data.held_balance) || 0);

      // Fetch transaction history
      const txRes = await api.get('/payments/transactions/');
      const mappedTx: Transaction[] = txRes.data.map((tx: any) => ({
        id: tx.id.toString(),
        name: tx.reason || 'Transaction',
        time: new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
        amount: parseFloat(tx.amount),
        type: tx.type === 'DEBIT' ? 'debit' : 'credit',
      }));
      setTransactions(mappedTx);

    } catch (error: any) {
      console.error("[WALLET] Fetch error:", error.response?.data || error.message);
      Alert.alert("Wallet Error", "Could not synchronize your wallet data at this time.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.white, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ marginTop: 20, fontSize: 16, color: Colors.textMuted }}>Syncing wallet...</Text>
      </View>
    );
  }

  return (
    <View className="flex-1" style={{ backgroundColor: Colors.background }}>
      <Sidebar visible={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {/* Header */}
      <View className="flex-row items-center justify-between px-4 pt-4 pb-3">
        <TouchableOpacity className="w-11 h-11 rounded-xl items-center justify-center shadow-sm" style={{ backgroundColor: Colors.primaryLight }} onPress={() => setSidebarOpen(true)}>
          <Ionicons name="menu" size={22} color={Colors.textMid} />
        </TouchableOpacity>
        <View className="flex-row gap-2">
          <TouchableOpacity className="w-11 h-11 rounded-xl items-center justify-center shadow-sm" style={{ backgroundColor: Colors.primaryLight }} onPress={() => router.push('/screens/search')}>
            <Ionicons name="search" size={20} color={Colors.textMid} />
          </TouchableOpacity>
          <TouchableOpacity className="w-11 h-11 rounded-xl items-center justify-center shadow-sm" style={{ backgroundColor: Colors.primaryLight }} onPress={() => router.push('/screens/notification')}>
            <Ionicons name="notifications-outline" size={20} color={Colors.textMid} />
          </TouchableOpacity>
        </View>
      </View>

      <FlatList
        data={transactions}
        keyExtractor={(item: Transaction) => item.id}
        initialNumToRender={10}
        maxToRenderPerBatch={10}
        windowSize={5}
        getItemLayout={(_data: any, index: number) => ({ length: 85, offset: 85 * index, index })}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 150 }}
        showsVerticalScrollIndicator={false}
        ListHeaderComponent={
          <>
            {/* Your Money card */}
            <View className="rounded-2xl py-5 items-center mb-4" style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
              <Text className="text-xl font-bold" style={{ color: Colors.primary }}>Your Wallet</Text>
            </View>

            {/* Balance cards */}
            <View className="flex-row gap-3 mb-7">
              <View className="flex-1 rounded-2xl py-6 px-4" style={{ backgroundColor: Colors.primaryBg, borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
                <Text className="text-3xl font-bold mb-1" style={{ color: Colors.textDark }}>₹{availableBalance.toFixed(2)}</Text>
                <Text className="text-sm font-medium" style={{ color: Colors.textSub }}>Available Balance</Text>
              </View>
              <View className="flex-1 rounded-2xl py-6 px-4" style={{ backgroundColor: Colors.primaryBg, borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
                <Text className="text-3xl font-bold mb-1" style={{ color: Colors.textDark }}>₹{heldBalance.toFixed(2)}</Text>
                <Text className="text-sm font-medium" style={{ color: Colors.textSub }}>Held (In-Trip)</Text>
              </View>
            </View>

            {/* Transactions header */}
            <View className="flex-row justify-between items-center mb-4">
              <Text className="text-xl font-bold" style={{ color: Colors.textDark }}>Transactions</Text>
              <TouchableOpacity>
                <Text className="text-base font-semibold" style={{ color: Colors.primary }}>See All</Text>
              </TouchableOpacity>
            </View>
          </>
        }
        ListEmptyComponent={
          <Text style={{ textAlign: 'center', marginTop: 40, color: Colors.textMuted }}>No transactions found</Text>
        }
        ListFooterComponent={
          <View style={{ paddingVertical: 20 }}>
            {transactions.length > 0 && <Text style={{ textAlign: 'center', color: Colors.textPlaceholder, fontSize: 13 }}>End of results</Text>}
          </View>
        }
        renderItem={({ item }: { item: Transaction }) => {
          const isDebit = item.type === 'debit';
          return (
            <View className="flex-row items-center rounded-2xl px-4 py-4 mb-3" style={{ backgroundColor: Colors.white, borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
              {/* Icon circle */}
              <View className="w-12 h-12 rounded-full items-center justify-center mr-4" style={{ backgroundColor: isDebit ? Colors.debitBg : Colors.creditBg }}>
                <Ionicons name={isDebit ? 'arrow-up' : 'arrow-down'} size={20} color={isDebit ? Colors.debitText : Colors.creditText} />
              </View>

              {/* Name & time */}
              <View className="flex-1">
                <Text className="text-base font-bold" style={{ color: Colors.textDark }}>{item.name}</Text>
                <Text className="text-sm mt-0.5" style={{ color: Colors.textMuted }}>{item.time}</Text>
              </View>

              {/* Amount */}
              <Text className="text-base font-bold" style={{ color: isDebit ? Colors.debitText : Colors.creditText }}>
                {isDebit ? `-₹${Math.abs(item.amount).toFixed(2)}` : `+₹${Math.abs(item.amount).toFixed(2)}`}
              </Text>
            </View>
          );
        }}
      />
    </View>
  );
}
