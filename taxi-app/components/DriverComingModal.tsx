import { View, Text, Modal, TouchableOpacity, Image, Alert, Linking } from 'react-native';
import React, { useState, useEffect, useRef } from 'react';
import { Ionicons, FontAwesome5 } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../constants/Colors';
import { api } from '../services/api';

type Props = {
  visible: boolean;
  onClose: () => void;
  onCancel?: () => void;
  vehicleName?: string;
  total?: string;
  paymentLabel?: string;
  paymentType?: string;
  paymentSub?: string;
  rideId?: string;
  rideStatus?: string;
  otp?: string;
};

function PaymentIcon({ type }: { type: string }) {
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
}

export default function DriverComingModal({
  visible,
  onClose,
  onCancel,
  vehicleName = 'Maruti Suzuki Dzire',
  total = '220',
  paymentLabel = '**** **** **** 8970',
  paymentType = 'visa',
  paymentSub = 'Expires: 12/26',
  rideId,
  rideStatus = 'SEARCHING',
  otp = '----'
}: Props) {
  const router = useRouter();
  const [devToolsOpen, setDevToolsOpen] = useState(true);
  const [seconds, setSeconds] = useState(215);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (visible) {
      setSeconds(215);
      timerRef.current = setInterval(() => {
        setSeconds((s) => (s > 0 ? s - 1 : 0));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [visible]);

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  const timeStr = `${mins}:${secs.toString().padStart(2, '0')}`;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.3)' }}>
        <View style={{ backgroundColor: Colors.white, borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingBottom: 36 }}>

          {/* Drag handle */}
          <View style={{ alignItems: 'center', paddingTop: 12, paddingBottom: 4 }}>
            <View style={{ width: 48, height: 5, borderRadius: 3, backgroundColor: '#D0D0D0' }} />
          </View>

          {/* Close */}
          <TouchableOpacity onPress={onClose} style={{ position: 'absolute', top: 16, right: 20, zIndex: 10 }}>
            <Ionicons name="close" size={26} color={Colors.textDark} />
          </TouchableOpacity>

          {/* Timer */}
          <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark, paddingHorizontal: 20, paddingTop: 8, paddingBottom: 16 }}>
            Your driver is coming in {timeStr}
          </Text>

          {/* Divider */}
          <View style={{ height: 1, backgroundColor: '#F0F0F0', marginBottom: 16 }} />

          {/* Driver info */}
          <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, marginBottom: 16 }}>
            <Image
              source={require('../assets/images/profile.jpg')}
              style={{ width: 72, height: 72, borderRadius: 36, marginRight: 14 }}
              resizeMode="cover"
            />
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark, marginBottom: 4 }}>Deepak</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                <Ionicons name="location-outline" size={14} color={Colors.textMuted} />
                <Text style={{ fontSize: 13, color: Colors.textMuted }}>800m (5mins away)</Text>
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                <Ionicons name="star" size={14} color={Colors.primary} />
                <Text style={{ fontSize: 13, color: Colors.textMuted }}>4.9 (531 reviews)</Text>
              </View>
            </View>
            <Image
              source={require('../assets/images/stylecar.jpg')}
              style={{ width: 100, height: 64 }}
              resizeMode="contain"
            />
          </View>

          {/* Divider */}
          <View style={{ height: 1, backgroundColor: '#F0F0F0', marginBottom: 16 }} />

          {/* Payment method + amount */}
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, marginBottom: 12 }}>
            <Text style={{ fontSize: 16, color: Colors.textMuted, fontWeight: '500' }}>Payment method</Text>
            <Text style={{ fontSize: 26, fontWeight: '700', color: Colors.textDark }}>₹{total}.00</Text>
          </View>

          {/* Payment card */}
          <View style={{ marginHorizontal: 20, flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFDE7', borderRadius: 10, borderWidth: 1.5, borderColor: Colors.primaryBorder, padding: 14, gap: 14, marginBottom: 20 }}>
            <PaymentIcon type={paymentType} />
            <View>
              <Text style={{ fontSize: 16, fontWeight: '600', color: Colors.textDark }}>{paymentLabel}</Text>
              {paymentSub ? <Text style={{ fontSize: 13, color: Colors.textMuted, marginTop: 2 }}>{paymentSub}</Text> : null}
            </View>
          </View>

          {/* Bottom actions */}
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20 }}>
            {/* Left: icon buttons */}
            <View style={{ flexDirection: 'row', gap: 12 }}>
              <TouchableOpacity
                onPress={() => Linking.openURL('tel:+919876543210')}
                style={{ width: 50, height: 50, borderRadius: 25, borderWidth: 2, borderColor: Colors.primary, alignItems: 'center', justifyContent: 'center' }}
              >
                <Ionicons name="call-outline" size={22} color={Colors.primary} />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => Alert.alert('Opening chat...')}
                style={{ width: 50, height: 50, borderRadius: 25, borderWidth: 2, borderColor: Colors.primary, alignItems: 'center', justifyContent: 'center' }}
              >
                <Ionicons name="chatbox-ellipses" size={22} color={Colors.primary} />
              </TouchableOpacity>
            </View>

            {/* Right: Cancel Ride */}
            <TouchableOpacity
              onPress={() => { onClose(); onCancel?.(); router.push('/screens/canceltaxi'); }}
              style={{ width: '55%', backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
            >
              <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.white }}>Cancel Ride</Text>
            </TouchableOpacity>
          </View>

          {/* 🛠️ DEVELOPER SIMULATION TOOLBAR — INSIDE MODAL */}
          {rideId && devToolsOpen && (
            <View style={{ marginTop: 24, marginHorizontal: 20, backgroundColor: '#222', padding: 10, borderRadius: 14, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
               <View style={{ flex: 1 }}>
                  <Text style={{ color: '#888', fontSize: 10, fontWeight: 'bold' }}>DEV SIMULATOR</Text>
                  <Text style={{ color: 'white', fontSize: 12, fontWeight: '600' }}>Status: {rideStatus}</Text>
               </View>

               {rideStatus === 'SEARCHING' && (
                 <TouchableOpacity onPress={() => api.post(`/rides/${rideId}/simulate-action/`, { action: 'ACCEPT' })} style={devBtnSmall}>
                    <Text style={{ color: 'white', fontSize: 11 }}>Accept</Text>
                 </TouchableOpacity>
               )}
               {rideStatus === 'ASSIGNED' && (
                 <TouchableOpacity onPress={() => api.post(`/rides/${rideId}/simulate-action/`, { action: 'ARRIVE' })} style={devBtnSmall}>
                    <Text style={{ color: 'white', fontSize: 11 }}>Arrive</Text>
                 </TouchableOpacity>
               )}
               {rideStatus === 'ARRIVED' && (
                 <TouchableOpacity onPress={() => api.post(`/rides/${rideId}/simulate-action/`, { action: 'START' })} style={devBtnSmall}>
                    <Text style={{ color: 'white', fontSize: 11 }}>Start (OTP:{otp})</Text>
                 </TouchableOpacity>
               )}
               {rideStatus === 'ONGOING' && (
                 <TouchableOpacity onPress={() => api.post(`/rides/${rideId}/simulate-action/`, { action: 'COMPLETE' })} style={devBtnSmall}>
                    <Text style={{ color: 'white', fontSize: 11 }}>Complete</Text>
                 </TouchableOpacity>
               )}
            </View>
          )}

        </View>
      </View>
    </Modal>
  );
}

const devBtnSmall = {
    backgroundColor: '#444',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#666',
};
