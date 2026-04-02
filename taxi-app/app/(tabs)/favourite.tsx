import { View, Text, TouchableOpacity, FlatList, Alert, ActivityIndicator, RefreshControl } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useFavourite } from '../../context/FavouriteContext';
import Colors from '../../constants/Colors';

export default function FavouriteScreen() {
  const router = useRouter();
  const { favourites, removeFavourite, loading, refresh } = useFavourite();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = async () => {
    setRefreshing(true);
    await refresh();
    setRefreshing(false);
  };

  const handleRemove = (id: string | number) => {
    Alert.alert('Remove Favourite', 'Are you sure you want to remove this place from your saved list?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => removeFavourite(id) },
    ]);
  };

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.background, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: Colors.background }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12, backgroundColor: Colors.white }}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}
        >
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid, marginLeft: 2 }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Saved Places</Text>
      </View>

      <FlatList
        data={favourites}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 150, gap: 12 }}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => (
          <View
            style={{ 
              flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.white, 
              borderRadius: 20, paddingHorizontal: 16, paddingVertical: 18,
              borderWidth: 1, borderColor: '#F0F0F0',
              shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1
            }}
          >
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: '#F3F4F6', alignItems: 'center', justifyContent: 'center', marginRight: 14 }}>
              <Ionicons name="location" size={24} color={Colors.textDark} />
            </View>

            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 17, fontWeight: '700', color: Colors.textDark, marginBottom: 2 }}>{item.label}</Text>
              <Text numberOfLines={1} style={{ fontSize: 13, color: Colors.textMuted }}>{item.address}</Text>
            </View>

            <TouchableOpacity onPress={() => handleRemove(item.id)} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <Ionicons name="trash-outline" size={22} color={Colors.removeBtnColor} />
            </TouchableOpacity>
          </View>
        )}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 80, paddingHorizontal: 40 }}>
            <View style={{ width: 80, height: 80, borderRadius: 40, backgroundColor: '#F3F4F6', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
              <Ionicons name="heart-outline" size={40} color="#D1D5DB" />
            </View>
            <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 8 }}>No saved places yet</Text>
            <Text style={{ fontSize: 14, color: Colors.textMuted, textAlign: 'center', lineHeight: 20 }}>Save your home, work, or favorite spots for quicker booking.</Text>
          </View>
        }
      />
    </View>
  );
}
