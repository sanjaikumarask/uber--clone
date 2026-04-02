import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Animated,
  StatusBar, Dimensions, ScrollView,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { api } from '../../services/api';
import Colors from '../../constants/Colors';

const { width, height } = Dimensions.get('window');

// Confetti particle
function ConfettiDot({ delay, color }: { delay: number; color: string }) {
  const anim = useRef(new Animated.Value(0)).current;
  const x = useRef(Math.random() * width).current;
  const size = useRef(6 + Math.random() * 8).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.delay(delay),
        Animated.timing(anim, { toValue: 1, duration: 2200 + Math.random() * 800, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0, duration: 0, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const translateY = anim.interpolate({ inputRange: [0, 1], outputRange: [-20, height * 0.6] });
  const opacity = anim.interpolate({ inputRange: [0, 0.1, 0.85, 1], outputRange: [0, 1, 1, 0] });
  const rotate = anim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', `${360 + Math.random() * 360}deg`] });

  return (
    <Animated.View
      style={{
        position: 'absolute', left: x, top: 0,
        width: size, height: size, borderRadius: size / 4,
        backgroundColor: color,
        opacity, transform: [{ translateY }, { rotate }],
      }}
    />
  );
}

const CONFETTI_COLORS = ['#F59E0B', Colors.primary, '#22C55E', '#EC4899', '#8B5CF6', '#F5A623'];

export default function PaymentSuccessScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ rideId: string }>();

  const checkScale = useRef(new Animated.Value(0)).current;
  const checkOpacity = useRef(new Animated.Value(0)).current;
  const cardTranslate = useRef(new Animated.Value(60)).current;
  const cardOpacity = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const [ride, setRide] = useState<any>(null);
  const [breakdown, setBreakdown] = useState<any>(null);

  useEffect(() => {
    // Entrance animation sequence
    Animated.sequence([
      Animated.delay(200),
      Animated.parallel([
        Animated.spring(checkScale, { toValue: 1, friction: 5, tension: 80, useNativeDriver: true }),
        Animated.timing(checkOpacity, { toValue: 1, duration: 300, useNativeDriver: true }),
      ]),
      Animated.delay(150),
      Animated.parallel([
        Animated.spring(cardTranslate, { toValue: 0, friction: 8, tension: 60, useNativeDriver: true }),
        Animated.timing(cardOpacity, { toValue: 1, duration: 400, useNativeDriver: true }),
      ]),
    ]).start();

    // Pulse the green ring
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.12, duration: 900, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 900, useNativeDriver: true }),
      ])
    ).start();

    // Fetch ride data
    if (params.rideId) {
      Promise.all([
        api.get(`/rides/${params.rideId}/`),
        api.get(`/rides/${params.rideId}/fare-breakdown/`).catch(() => null),
      ]).then(([rideRes, breakdownRes]) => {
        setRide(rideRes.data);
        if (breakdownRes) setBreakdown(breakdownRes.data);
      }).catch(() => {});
    }
  }, []);

  const goToRating = () => {
    router.replace({
      pathname: '/screens/rate-driver',
      params: { rideId: params.rideId },
    });
  };

  const goHome = () => {
    router.replace('/(tabs)');
  };

  const confettiDots = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    delay: i * 80,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  }));

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor={Colors.white} />

      {/* Confetti */}
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        {confettiDots.map(d => (
          <ConfettiDot key={d.id} delay={d.delay} color={d.color} />
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* ✅ Success Icon */}
        <View style={styles.iconWrap}>
          <Animated.View style={[styles.pulseRing, { transform: [{ scale: pulseAnim }] }]} />
          <Animated.View style={[styles.checkCircle, { transform: [{ scale: checkScale }], opacity: checkOpacity }]}>
            <Ionicons name="checkmark" size={52} color="#fff" />
          </Animated.View>
        </View>

        <Text style={styles.title}>Payment{'\n'}Successful!</Text>
        <Text style={styles.subtitle}>Your ride has been paid. Thanks for choosing Tripzo.</Text>

        {/* Fare Card */}
        <Animated.View style={[styles.fareCard, { transform: [{ translateY: cardTranslate }], opacity: cardOpacity }]}>
          <LinearGradient
            colors={[Colors.primaryLight, Colors.primaryBg]}
            style={styles.fareGradient}
          >
            <Text style={styles.fareLabel}>AMOUNT PAID</Text>
            <Text style={styles.fareAmount}>
              ₹{breakdown?.total_with_tip || ride?.final_fare || '—'}
            </Text>

            {ride && (
              <>
                <View style={styles.divider} />
                <View style={styles.infoRow}>
                  <Ionicons name="location-outline" size={14} color={Colors.textMid} />
                  <Text style={styles.infoText} numberOfLines={1}>
                    {ride.pickup_address}
                  </Text>
                </View>
                <View style={[styles.infoRow, { marginTop: 6 }]}>
                  <Ionicons name="navigate-outline" size={14} color={Colors.primary} />
                  <Text style={styles.infoText} numberOfLines={1}>
                    {ride.drop_address}
                  </Text>
                </View>

                {ride.driver && (
                  <>
                    <View style={styles.divider} />
                    <View style={styles.driverRow}>
                      <View style={styles.driverAvatar}>
                        <Text style={styles.avatarEmoji}>👨‍✈️</Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.driverName}>
                          {ride.driver.user?.first_name || 'Your Driver'}
                        </Text>
                        <Text style={styles.driverVehicle}>
                          {ride.driver.vehicle_model} · {ride.driver.vehicle_number}
                        </Text>
                      </View>
                      <View style={styles.paidBadge}>
                        <Text style={styles.paidBadgeText}>PAID</Text>
                      </View>
                    </View>
                  </>
                )}
              </>
            )}
          </LinearGradient>
        </Animated.View>

        {/* Breakdown mini summary */}
        {breakdown && (
          <Animated.View style={[styles.breakdownCard, { opacity: cardOpacity }]}>
            {[
              { label: 'Base Fare', value: `₹${breakdown.base_fare}` },
              breakdown.distance_charge > 0 && { label: `Distance (${breakdown.actual_distance_km} km)`, value: `₹${breakdown.distance_charge}` },
              parseFloat(breakdown.surge_multiplier) > 1 && { label: `Surge (${breakdown.surge_multiplier}x)`, value: 'Applied', accent: Colors.primary },
              parseFloat(breakdown.discount_amount) > 0 && { label: 'Discount', value: `-₹${breakdown.discount_amount}`, accent: '#22C55E' },
              parseFloat(breakdown.tip_amount) > 0 && { label: 'Tip', value: `₹${breakdown.tip_amount}`, accent: Colors.primary },
            ].filter(Boolean).map((item: any, idx) => (
              <View key={idx} style={styles.breakdownRow}>
                <Text style={styles.breakdownLabel}>{item.label}</Text>
                <Text style={[styles.breakdownValue, item.accent && { color: item.accent }]}>
                  {item.value}
                </Text>
              </View>
            ))}
          </Animated.View>
        )}

        {/* CTAs */}
        <Animated.View style={[styles.ctas, { opacity: cardOpacity }]}>
          <TouchableOpacity style={styles.primaryBtn} onPress={goToRating} activeOpacity={0.85}>
            <LinearGradient
              colors={[Colors.primary, '#E69500']}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              style={styles.primaryBtnInner}
            >
              <Text style={styles.primaryBtnText}>Rate & Tip Driver</Text>
              <Ionicons name="star" size={18} color={Colors.white} style={{ marginLeft: 8 }} />
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryBtn} onPress={goHome} activeOpacity={0.7}>
            <Text style={styles.secondaryBtnText}>Go Home</Text>
          </TouchableOpacity>
        </Animated.View>

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Colors.white },
  scroll: { alignItems: 'center', paddingTop: 80, paddingBottom: 60, paddingHorizontal: 24 },

  // Icon
  iconWrap: { alignItems: 'center', justifyContent: 'center', marginBottom: 28 },
  pulseRing: {
    position: 'absolute',
    width: 120, height: 120, borderRadius: 60,
    borderWidth: 2, borderColor: 'rgba(34,197,94,0.3)',
  },
  checkCircle: {
    width: 96, height: 96, borderRadius: 48,
    backgroundColor: '#22C55E',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#22C55E', shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.5, shadowRadius: 20, elevation: 12,
  },

  title: {
    fontSize: 42, fontWeight: '900', color: Colors.textDark,
    textAlign: 'center', letterSpacing: -1.5, lineHeight: 48,
    marginBottom: 12,
  },
  subtitle: { fontSize: 15, color: Colors.textSub, textAlign: 'center', marginBottom: 36, lineHeight: 22 },

  // Fare card
  fareCard: { width: '100%', borderRadius: 24, overflow: 'hidden', marginBottom: 16, borderWidth: 1.5, borderColor: Colors.primaryBorder, shadowColor: Colors.shadow, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  fareGradient: { padding: 24, borderRadius: 24 },
  fareLabel: { fontSize: 11, fontWeight: '800', color: Colors.textMid, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 8 },
  fareAmount: { fontSize: 48, fontWeight: '900', color: Colors.textDark, letterSpacing: -2, marginBottom: 4 },

  divider: { height: 1, backgroundColor: '#E0E0E0', marginVertical: 16 },

  infoRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  infoText: { flex: 1, fontSize: 13, color: Colors.textSub, fontWeight: '500' },

  driverRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  driverAvatar: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#F0F0F0',
    alignItems: 'center', justifyContent: 'center',
  },
  avatarEmoji: { fontSize: 20 },
  driverName: { fontSize: 15, fontWeight: '800', color: Colors.textDark },
  driverVehicle: { fontSize: 12, color: Colors.textSub, marginTop: 2 },
  paidBadge: {
    backgroundColor: 'rgba(34,197,94,0.15)',
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8,
  },
  paidBadgeText: { fontSize: 11, fontWeight: '900', color: '#22C55E', letterSpacing: 0.5 },

  // Breakdown
  breakdownCard: {
    width: '100%', backgroundColor: '#F9F9F9',
    borderRadius: 18, padding: 20, gap: 10, marginBottom: 28,
    borderWidth: 1, borderColor: '#E5E5E5',
  },
  breakdownRow: { flexDirection: 'row', justifyContent: 'space-between' },
  breakdownLabel: { fontSize: 13, color: Colors.textSub, fontWeight: '500' },
  breakdownValue: { fontSize: 13, color: Colors.textMid, fontWeight: '700' },

  // CTAs
  ctas: { width: '100%', gap: 14 },
  primaryBtn: { width: '100%', borderRadius: 18, overflow: 'hidden', shadowColor: Colors.primary, shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.25, shadowRadius: 10, elevation: 6 },
  primaryBtnInner: {
    paddingVertical: 20, alignItems: 'center', justifyContent: 'center',
    flexDirection: 'row',
  },
  primaryBtnText: { fontSize: 18, fontWeight: '900', color: Colors.white },
  secondaryBtn: { alignItems: 'center', paddingVertical: 14 },
  secondaryBtnText: { fontSize: 16, fontWeight: '700', color: Colors.textSub },
});
