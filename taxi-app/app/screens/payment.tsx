import { View, Text, TouchableOpacity, Image, ScrollView, ActivityIndicator, Alert } from 'react-native';
import React, { useState } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons, FontAwesome5 } from '@expo/vector-icons';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

const PAYMENT_METHODS = [
  { id: 'visa', label: '**** **** **** 8970', sub: 'Expires: 12/26', type: 'visa' },
  { id: 'mastercard', label: '**** **** **** 8970', sub: 'Expires: 12/26', type: 'mastercard' },
  { id: 'paypal', label: 'mailaddress@mail.com', sub: 'Expires: 12/26', type: 'paypal' },
  { id: 'cash', label: 'Cash', sub: '', type: 'cash' },
];

const VEHICLE_DATA: Record<string, { name: string; rating: string; reviews: string; image: any; rate: number; type: string }> = {
  car: { name: 'Maruti Suzuki Dzire', rating: '4.9', reviews: '531', image: require('../../assets/images/stylecar.jpg'), rate: 200, type: 'go' },
  bike: { name: 'Honda CB Shine', rating: '4.7', reviews: '312', image: require('../../assets/images/bike.jpg'), rate: 80, type: 'moto' },
  taxi: { name: 'Toyota Innova', rating: '4.8', reviews: '420', image: require('../../assets/images/taxi.jpg'), rate: 250, type: 'xl' },
  cycle: { name: 'Trek FX3', rating: '4.5', reviews: '180', image: require('../../assets/images/cycle.jpg'), rate: 30, type: 'bicycle' },
};

const VAT_RATE = 0.05;
const PROMO = 5;

export default function PaymentScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    transport: string;
    destName: string;
    destAddress: string;
    destLat: string;
    destLng: string;
    pickupLat?: string;
    pickupLng?: string;
    pickupAddress?: string;
    real_total_fare?: string;
    surge?: string;
  }>();

  const transport = params.transport || 'car';
  const vehicle = VEHICLE_DATA[transport] ?? VEHICLE_DATA.car;

  const [selectedPayment, setSelectedPayment] = useState('visa');
  const [loading, setLoading] = useState(false);

  // Use real fare from estimate API if available, otherwise fallback to vehicle rate
  const total = params.real_total_fare ? parseInt(params.real_total_fare) : (vehicle.rate + Math.round(vehicle.rate * VAT_RATE) - PROMO);
  const vat = params.real_total_fare ? Math.round(total * 0.05) : Math.round(vehicle.rate * VAT_RATE);

  const handleConfirmRide = async () => {
    if (loading) return;
    setLoading(true);

    try {
      // 🚀 REAL API CALL: Create ride in backend (Endpoint is /rides/)
      // Ensure all numbers are valid to avoid 400 Bad Request
      const body = {
        pickup_lat: Number(params.pickupLat) || 13.0827,
        pickup_lng: Number(params.pickupLng) || 80.2707,
        pickup_address: params.pickupAddress || 'Current Location',
        drop_lat: Number(params.destLat) || 13.0827,
        drop_lng: Number(params.destLng) || 80.2707,
        drop_address: params.destName || params.destAddress || 'Destination',
        vehicle_type: vehicle.type,
        estimated_fare: Number(total) || 0
      };

      const response = await api.post('/rides/', body);

      const { id: rideId } = response.data;
      await AsyncStorage.setItem('active_ride_id', String(rideId));

      // On Success: Navigate to home with rideId for tracking
      router.replace({
        pathname: '/(tabs)',
        params: {
          driverComing: '1',
          rideId: rideId,
          vehicleName: vehicle.name,
          total: String(total),
          paymentLabel: PAYMENT_METHODS.find(m => m.id === selectedPayment)?.label ?? '',
          paymentType: PAYMENT_METHODS.find(m => m.id === selectedPayment)?.type ?? 'visa',
          paymentSub: PAYMENT_METHODS.find(m => m.id === selectedPayment)?.sub ?? ''
        }
      });

    } catch (error: any) {
      console.error("[PAYMENT] Create ride failed:", error.response?.data || error.message);

      // Handle "Active ride exists" by redirecting to home
      if (error.response?.status === 409 && error.response?.data?.ride_id) {
        const rideId = error.response.data.ride_id;
        Alert.alert(
          "Active Ride Found",
          "You already have a ride in progress. Reconnecting you now...",
          [{
            text: "Continue Tracking",
            onPress: () => router.replace({
              pathname: '/(tabs)',
              params: {
                rideId: String(rideId),
                driverComing: '1',
                vehicleName: vehicle.name,
                total: String(total)
              }
            })
          }]
        );
        return;
      }

      Alert.alert(
        "Booking Failed",
        error.response?.data?.error || "We couldn't create your ride request. Please try again.",
        [
          { text: "Cancel", style: "cancel" },
          { text: "Retry", onPress: handleConfirmRide }
        ]
      );
    } finally {
      setLoading(false);
    }
  };

  const PaymentIcon = ({ type }: { type: string }) => {
    if (type === 'visa')
      return (
        <View style={{ width: 56, height: 38, backgroundColor: '#1A1F71', borderRadius: 6, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={{ color: '#fff', fontWeight: '900', fontSize: 16, fontStyle: 'italic' }}>VISA</Text>
        </View>
      );
    if (type === 'mastercard')
      return (
        <View style={{ width: 56, height: 38, alignItems: 'center', justifyContent: 'center' }}>
          <View style={{ flexDirection: 'row' }}>
            <View style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: '#EB001B', opacity: 0.9 }} />
            <View style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: '#F79E1B', opacity: 0.9, marginLeft: -12 }} />
          </View>
          <Text style={{ fontSize: 7, color: Colors.textMuted, marginTop: 2 }}>mastercard</Text>
        </View>
      );
    if (type === 'paypal')
      return (
        <View style={{ width: 56, height: 38, alignItems: 'center', justifyContent: 'center' }}>
          <FontAwesome5 name="paypal" size={30} color="#003087" />
        </View>
      );
    return (
      <View style={{ width: 56, height: 38, backgroundColor: '#8E8E93', borderRadius: 10, alignItems: 'center', justifyContent: 'center' }}>
        <FontAwesome5 name="dollar-sign" size={20} color="#fff" />
      </View>
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingTop: 20, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', position: 'absolute', left: 20 }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textDark} />
          <Text style={{ fontSize: 18, color: Colors.textDark, fontWeight: '500' }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ flex: 1, textAlign: 'center', fontSize: 20, fontWeight: '800', color: Colors.textDark }}>Payment</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 120 }} showsVerticalScrollIndicator={false}>

        {/* Vehicle card */}
        <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFDE7', borderRadius: 16, borderWidth: 1.5, borderColor: Colors.primaryBorder, padding: 16, marginBottom: 24 }}>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 18, fontWeight: '800', color: Colors.textDark, marginBottom: 6 }}>{vehicle.name}</Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Ionicons name="star" size={16} color={Colors.primary} />
              <Text style={{ fontSize: 14, color: Colors.textMuted }}>{vehicle.rating} ({vehicle.reviews} reviews)</Text>
            </View>
          </View>
          <Image source={vehicle.image} style={{ width: 110, height: 70 }} resizeMode="contain" />
        </View>

        {/* Charge section */}
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark, marginBottom: 14 }}>Charge</Text>

        <View style={{ gap: 0 }}>
          <ChargeRow label={`${vehicle.name.split(' ').slice(-1)[0]} /per hours`} value={`₹${vehicle.rate}`} />
          <ChargeRow label="Vat (5%)" value={`₹${vat}`} />
          <ChargeRow label="Promo Code" value={`-₹${PROMO}`} />
          <View style={{ height: 1, backgroundColor: '#E0E0E0', marginVertical: 10 }} />
          <ChargeRow label="Total" value={`₹${total}`} bold />
        </View>

        {/* Payment method */}
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 28, marginBottom: 16 }}>
          <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Select payment method</Text>
          <TouchableOpacity>
            <Text style={{ fontSize: 15, fontWeight: '600', color: Colors.primary }}>View All</Text>
          </TouchableOpacity>
        </View>

        <View style={{ gap: 12 }}>
          {PAYMENT_METHODS.map((method) => {
            const isSelected = selectedPayment === method.id;
            return (
              <TouchableOpacity
                key={method.id}
                onPress={() => setSelectedPayment(method.id)}
                style={{
                  flexDirection: 'row', alignItems: 'center',
                  borderWidth: 1.5,
                  borderColor: isSelected ? Colors.primary : Colors.primaryBorder,
                  backgroundColor: isSelected ? '#FFFDE7' : Colors.white,
                  borderRadius: 10, padding: 14, gap: 14,
                }}
              >
                <PaymentIcon type={method.type} />
                <View>
                  <Text style={{ fontSize: 16, fontWeight: '600', color: isSelected ? Colors.textDark : Colors.textMuted }}>{method.label}</Text>
                  {method.sub ? <Text style={{ fontSize: 13, color: Colors.textMuted, marginTop: 2 }}>{method.sub}</Text> : null}
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>


      <View style={{ position: 'absolute', bottom: 0, left: 0, right: 0, paddingHorizontal: 20, paddingBottom: 32, paddingTop: 12, backgroundColor: Colors.white }}>
        <TouchableOpacity
          disabled={loading}
          onPress={handleConfirmRide}
          style={{ backgroundColor: loading ? Colors.textPlaceholder : Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
        >
          {loading ? (
            <ActivityIndicator color={Colors.white} />
          ) : (
            <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Confirm Ride</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

function ChargeRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8 }}>
      <Text style={{ fontSize: 15, color: bold ? Colors.textDark : Colors.textMuted, fontWeight: bold ? '700' : '400' }}>{label}</Text>
      <Text style={{ fontSize: 15, color: Colors.textDark, fontWeight: bold ? '700' : '400' }}>{value}</Text>
    </View>
  );
}
