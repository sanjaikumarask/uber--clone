import { View, Text, TouchableOpacity, Image, Dimensions, ActivityIndicator, ScrollView, Alert } from 'react-native';
import React, { useState, useEffect } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

const { width } = Dimensions.get('window');
const CARD_SIZE = (width - 48 - 12) / 2 - 16;

type VehicleType = {
  id: string;
  name: string;
  type: string; // 'go', 'moto', 'xl', etc.
  image: any;
  base_fare: number;
};

const UI_ASSETS: Record<string, any> = {
  car: require('../../assets/images/car.jpg'),
  bike: require('../../assets/images/bike.jpg'),
  taxi: require('../../assets/images/taxi.jpg'),
  cycle: require('../../assets/images/cycle.jpg'),
  go: require('../../assets/images/car.jpg'),
  moto: require('../../assets/images/bike.jpg'),
  xl: require('../../assets/images/taxi.jpg'),
  bicycle: require('../../assets/images/cycle.jpg'),
};

export default function SelectTransportScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ 
    destLat: string; 
    destLng: string; 
    pickupLat: string; 
    pickupLng: string;
    destName: string;
    destAddress: string;
  }>();

  const [vehicles, setVehicles] = useState<VehicleType[]>([]);
  const [estimates, setEstimates] = useState<Record<string, any>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Fare Config (Available Vehicle Types)
      const configRes = await api.get('/rides/fare-config/');
      const backendVehicles = configRes.data.results || configRes.data;
      
      const mappedVehicles = backendVehicles.map((v: any) => {
        const vType = v.vehicle_type || v.type || 'go'; // Fallback to 'go' if both are missing
        return {
          id: vType,
          name: v.name || vType.toUpperCase(),
          type: vType,
          base_fare: parseFloat(v.base_fare || 0),
          image: UI_ASSETS[vType] || UI_ASSETS.car
        };
      });
      setVehicles(mappedVehicles);

      // 2. Fetch Estimates for the route
      if (params.pickupLat && params.destLat) {
        // FIXED: Backend is /rides/estimate-fare/
        const estimateRes = await api.post('/rides/estimate-fare/', {
          pickup_lat: parseFloat(params.pickupLat),
          pickup_lng: parseFloat(params.pickupLng),
          drop_lat: parseFloat(params.destLat || '0'), 
          drop_lng: parseFloat(params.destLng || '0'),
        });
        
        setEstimates(estimateRes.data);
      }

    } catch (error: any) {
      console.error("[SELECT_TRANSPORT] Fetch failed:", error.response?.data || error.message);
      Alert.alert("Sync Error", "Could not fetch latest rates. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (vehicle: VehicleType) => {
    setSelected(vehicle.id);
    const vehiclePrice = estimates.prices?.[vehicle.id] || vehicle.base_fare;
    
    // Navigate to payment with real data
    router.push({ 
        pathname: '/screens/payment', 
        params: { 
            ...params,
            transport: vehicle.id,
            real_total_fare: String(vehiclePrice),
            surge: estimates.surge_multiplier || 1.0
        } 
    });
  };

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.white, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ marginTop: 20, fontSize: 16, color: Colors.textMuted }}>Fetching latest fares...</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white, paddingHorizontal: 24, paddingTop: 20 }}>
      {/* Back */}
      <TouchableOpacity onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 32 }}>
        <Ionicons name="chevron-back" size={22} color={Colors.textDark} />
        <Text style={{ fontSize: 18, color: Colors.textDark, fontWeight: '500' }}>Back</Text>
      </TouchableOpacity>

      {/* Title */}
      <Text style={{ fontSize: 26, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 12 }}>
        Select your transport
      </Text>
      <Text style={{ fontSize: 14, color: Colors.textMuted, textAlign: 'center', marginBottom: 32 }}>
        Live fares for your trip to {params.destName || 'Destination'}
      </Text>

      {/* 2x2 Grid */}
      <ScrollView contentContainerStyle={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12, justifyContent: 'center' }}>
        {vehicles.map((item) => {
          const isSelected = selected === item.id;
          // Use specific price from the prices map for this type
          const displayFare = estimates.prices?.[item.id] || item.base_fare;
          
          return (
            <TouchableOpacity
              key={item.id}
              onPress={() => handleSelect(item)}
              style={{
                width: CARD_SIZE,
                height: CARD_SIZE + 20,
                backgroundColor: isSelected ? '#E1F5FE' : '#FFFDE7',
                borderRadius: 12,
                borderWidth: 1.5,
                borderColor: isSelected ? Colors.primary : Colors.primaryBorder,
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <Image source={item.image} style={{ width: CARD_SIZE * 0.55, height: CARD_SIZE * 0.55 }} resizeMode="contain" />
              <Text style={{ fontSize: 16, color: Colors.textDark, fontWeight: '700' }}>{item.name}</Text>
              <Text style={{ fontSize: 15, color: Colors.primary, fontWeight: '800' }}>₹{displayFare}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}
