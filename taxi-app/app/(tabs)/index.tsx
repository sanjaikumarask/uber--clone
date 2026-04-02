import { View, Text, TouchableOpacity, Image, Platform, Modal, ActivityIndicator } from 'react-native';
import React, { useRef, useEffect, useState } from 'react';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import { Ionicons, MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import Colors from '../../constants/Colors';
import { useRouter, useLocalSearchParams } from 'expo-router';
import Sidebar from '../../components/Sidebar';
import SelectAddressModal from '../../components/SelectAddressModal';
import DriverComingModal from '../../components/DriverComingModal';
import { useFavourite } from '../../context/FavouriteContext';
import { api } from '../../services/api';

const TAB_BAR_HEIGHT = Platform.OS === 'ios' ? 88 : 70;

import { SocketService } from '../../services/socket';

export default function HomeScreen() {
  const mapRef = useRef<MapView>(null);
  const router = useRouter();
  const params = useLocalSearchParams<{ rideId?: string; driverComing?: string; vehicleName?: string; total?: string; paymentLabel?: string; paymentType?: string; paymentSub?: string }>();

  const [locationModalVisible, setLocationModalVisible] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [driverCoord, setDriverCoord] = useState<{ latitude: number; longitude: number } | null>(null);
  const [address, setAddress] = useState('Fetching location...');
  const [cardHeight, setCardHeight] = useState(150);
  const [selectModalVisible, setSelectModalVisible] = useState(false);
  const [driverModalVisible, setDriverModalVisible] = useState(false);
  const [trackingActive, setTrackingActive] = useState(false);
  const [rideStatus, setRideStatus] = useState<string>('SEARCHING');
  const [otp, setOtp] = useState<string>('');
  const [devToolsOpen, setDevToolsOpen] = useState(true);
  const watchRef = useRef<Location.LocationSubscription | null>(null);

  const [markerReady, setMarkerReady] = useState(false);
  const { favourites, addFavourite, removeFavourite, isFavourite } = useFavourite();

  const handleHeartPress = async () => {
    if (!address || address === 'Fetching location...' || address === 'Location permission denied') return;
    if (isFavourite(address)) {
      const fav = favourites.find(f => f.address === address);
      if (fav) await removeFavourite(fav.id);
    } else {
      await addFavourite(address);
    }
  };

  const [wsStatus, setWsStatus] = useState<string>('DISCONNECTED');

  // Show driver modal when navigated back from payment
  useEffect(() => {
    if (params.driverComing === '1' && params.rideId) {
      setDriverModalVisible(true);
      setTrackingActive(true);
      
      // 🔥 Integration: Connect to WebSocket with state monitoring
      SocketService.setStateListener((state) => {
        setWsStatus(state);
      });

      (async () => {
          try {
              const res = await api.get(`/rides/${params.rideId}/`);
              setRideStatus(res.data.status);
              setOtp(res.data.otp_code);
          } catch (e) {
              console.warn('[WS] Failed to fetch initial ride state', e);
          }
          SocketService.connect(params.rideId);
      })();

      const unsub = SocketService.on('DRIVER_LOCATION_UPDATED', (data) => {
        if (data.lat && data.lng) {
          setDriverCoord({ latitude: parseFloat(data.lat), longitude: parseFloat(data.lng) });
        }
      });

      const unsubStatus = SocketService.on('RIDE_STATUS_UPDATED', (data) => {
        setRideStatus(data.status);
        if (data.status === 'COMPLETED') {
          setTrackingActive(false);
          setDriverModalVisible(false);
          // 🔥 Navigating to Summary screen instead of alert
          router.replace({
             pathname: '/screens/summary',
             params: { rideId: params.rideId }
          });
        }
      });

      return () => {
        unsub();
        unsubStatus();
        SocketService.disconnect();
      };
    }
  }, [params.driverComing, params.rideId]);

  const startLocationWatch = async () => {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      setLocationModalVisible(true);
      setAddress('Location permission denied');
      return;
    }
    const initial = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
    const coords = { latitude: initial.coords.latitude, longitude: initial.coords.longitude };
    setLocation(coords);
    animateTo(coords);
    reverseGeocode(coords);
    watchRef.current = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.High, distanceInterval: 5, timeInterval: 3000 },
      (loc) => {
        const updated = { latitude: loc.coords.latitude, longitude: loc.coords.longitude };
        setLocation(updated);
        reverseGeocode(updated);
      }
    );
  };

  useEffect(() => {
    startLocationWatch();
    return () => { watchRef.current?.remove(); };
  }, []);

  const animateTo = (coords: { latitude: number; longitude: number }) => {
    mapRef.current?.animateToRegion({ ...coords, latitudeDelta: 0.015, longitudeDelta: 0.015 }, 800);
  };

  const reverseGeocode = async (coords: { latitude: number; longitude: number }) => {
    try {
      const result = await Location.reverseGeocodeAsync(coords);
      if (result.length > 0) {
        const r = result[0];
        const parts = [r.street, r.district, r.city].filter(Boolean);
        setAddress(parts.join(', ') || 'Current Location');
      }
    } catch {
      setAddress('Current Location');
    }
  };

  return (
    <View style={{ flex: 1 }}>
      <Sidebar visible={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <MapView
        ref={mapRef}
        style={{ flex: 1 }}
        provider={PROVIDER_GOOGLE}
        initialRegion={{ latitude: 13.0827, longitude: 80.2707, latitudeDelta: 0.015, longitudeDelta: 0.015 }}
        showsUserLocation={false}
        showsMyLocationButton={false}
      >
        {/* User location marker — normal pin when not tracking, car image when tracking */}
        {location && (
          <Marker coordinate={location} anchor={{ x: 0.5, y: 0.5 }} tracksViewChanges={!markerReady}>
            {trackingActive ? (
              <Image
                source={require('../../assets/images/Trackcar2.jpg')}
                style={{ width: 52, height: 52 }}
                resizeMode="contain"
              />
            ) : (
              <View
                onLayout={() => setTimeout(() => setMarkerReady(true), 300)}
                style={{
                  width: 44, height: 44, borderRadius: 22,
                  backgroundColor: Colors.primary,
                  alignItems: 'center', justifyContent: 'center',
                }}
              >
                <Ionicons name="location" size={24} color="#fff" />
              </View>
            )}
          </Marker>
        )}

        {/* Driver car marker — stays visible while tracking */}
        {trackingActive && driverCoord && (
          <Marker coordinate={driverCoord} anchor={{ x: 0.5, y: 0.5 }}>
            <Image
              source={require('../../assets/images/Trackcar1.jpg')}
              style={{ width: 52, height: 52 }}
              resizeMode="contain"
            />
          </Marker>
        )}

        {/* Route polyline — stays visible while tracking */}
        {trackingActive && driverCoord && location && (
          <Polyline
            coordinates={[driverCoord, location]}
            strokeColor={Colors.primary}
            strokeWidth={4}
            lineDashPattern={[0]}
          />
        )}
      </MapView>

      {/* Header */}
      <View style={{ position: 'absolute', top: 16, left: 16, right: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <TouchableOpacity style={styles.headerBtn} onPress={() => setSidebarOpen(true)}>
          <Ionicons name="menu" size={22} color={Colors.textMid} />
        </TouchableOpacity>

        {/* Real-time Status Badge */}
        {wsStatus === 'CONNECTING' && (
          <View style={{ backgroundColor: '#FFF9C4', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, flexDirection: 'row', alignItems: 'center', gap: 6, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 }}>
            <ActivityIndicator size="small" color="#FBC02D" />
            <Text style={{ fontSize: 13, fontWeight: '600', color: '#FBC02D' }}>Connecting...</Text>
          </View>
        )}

        <View style={{ flexDirection: 'row', gap: 10 }}>
          <TouchableOpacity style={styles.headerBtn} onPress={() => router.push('/screens/search')}>
            <Ionicons name="search" size={20} color={Colors.textMid} />
          </TouchableOpacity>
          <TouchableOpacity style={styles.headerBtn} onPress={() => router.push('/screens/notification')}>
            <Ionicons name="notifications-outline" size={20} color={Colors.textMid} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Recenter button — hide when driver modal is open */}
      {!driverModalVisible && (
        <TouchableOpacity
          onPress={() => location && animateTo(location)}
          style={{ position: 'absolute', right: 16, bottom: TAB_BAR_HEIGHT + cardHeight + 24, width: 44, height: 44, backgroundColor: Colors.white, borderRadius: 22, alignItems: 'center', justifyContent: 'center', shadowColor: Colors.shadow, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.12, shadowRadius: 4, elevation: 4 }}
        >
          <MaterialIcons name="my-location" size={22} color={Colors.textSub} />
        </TouchableOpacity>
      )}

      {/* Bottom location card — hide when driver modal is open */}
      {!driverModalVisible && (
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={() => setSelectModalVisible(true)}
          onLayout={(e) => setCardHeight(e.nativeEvent.layout.height)}
          style={{ position: 'absolute', bottom: TAB_BAR_HEIGHT + 12, left: 16, right: 16, backgroundColor: Colors.primaryBg, borderRadius: 20, borderWidth: 1.5, borderColor: Colors.primaryBorderStrong, padding: 12, gap: 10, shadowColor: Colors.shadow, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 5 }}
        >
          <View style={styles.inputRow}>
            <MaterialCommunityIcons name="crosshairs-gps" size={20} color={Colors.textMuted} />
            <Text numberOfLines={1} style={{ flex: 1, marginLeft: 10, fontSize: 15, color: address === 'Fetching location...' ? Colors.textPlaceholder : Colors.textMid }}>
              {address}
            </Text>
            <TouchableOpacity onPress={handleHeartPress} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Ionicons
                name={isFavourite(address) ? 'heart' : 'heart-outline'}
                size={20}
                color={isFavourite(address) ? Colors.removeBtnColor : Colors.textPlaceholder}
              />
            </TouchableOpacity>
          </View>
          <View style={styles.inputRow}>
            <Ionicons name="location-outline" size={20} color={Colors.textMuted} />
            <Text style={{ flex: 1, marginLeft: 10, fontSize: 15, color: Colors.textPlaceholder }}>Enter destination</Text>
          </View>
        </TouchableOpacity>
      )}

      <SelectAddressModal 
        visible={selectModalVisible} 
        onClose={() => setSelectModalVisible(false)} 
        currentAddress={address} 
        currentLocation={location || { latitude: 13.0827, longitude: 80.2707 }}
      />

      <DriverComingModal
        visible={driverModalVisible}
        onClose={() => setDriverModalVisible(false)}
        onCancel={() => { setDriverModalVisible(false); setTrackingActive(false); }}
        vehicleName={params.vehicleName ?? 'Maruti Suzuki Dzire'}
        total={params.total ?? '220'}
        paymentLabel={params.paymentLabel ?? '**** **** **** 8970'}
        paymentType={params.paymentType ?? 'visa'}
        paymentSub={params.paymentSub ?? 'Expires: 12/26'}
        rideId={params.rideId}
        rideStatus={rideStatus}
        otp={otp}
      />

      {/* Location Permission Modal */}
      <Modal visible={locationModalVisible} transparent animationType="fade" onRequestClose={() => setLocationModalVisible(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 }}>
          <View style={{ backgroundColor: Colors.white, borderRadius: 28, paddingHorizontal: 28, paddingTop: 36, paddingBottom: 28, width: '100%', alignItems: 'center' }}>

            {/* Layered circle icon */}
            <View style={{ width: 120, height: 120, borderRadius: 60, backgroundColor: 'rgba(245,166,35,0.12)', alignItems: 'center', justifyContent: 'center', marginBottom: 28 }}>
              <View style={{ width: 90, height: 90, borderRadius: 45, backgroundColor: 'rgba(245,166,35,0.22)', alignItems: 'center', justifyContent: 'center' }}>
                <View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: Colors.primary, alignItems: 'center', justifyContent: 'center' }}>
                  <Ionicons name="location" size={30} color={Colors.textDark} />
                </View>
              </View>
            </View>

            {/* Title */}
            <Text style={{ fontSize: 26, fontWeight: '800', color: Colors.textDark, textAlign: 'center', marginBottom: 10 }}>
              Enable your location
            </Text>

            {/* Subtitle */}
            <Text style={{ fontSize: 15, color: Colors.textMuted, textAlign: 'center', lineHeight: 24, marginBottom: 28 }}>
              Choose your location to start find the request around you
            </Text>

            {/* Use my location */}
            <TouchableOpacity
              onPress={() => { setLocationModalVisible(false); startLocationWatch(); }}
              style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center', width: '100%', marginBottom: 12 }}
            >
              <Text style={{ fontSize: 17, fontWeight: '700', color: Colors.white }}>Use my location</Text>
            </TouchableOpacity>

            {/* Skip Now */}
            <TouchableOpacity
              onPress={() => setLocationModalVisible(false)}
              style={{ borderWidth: 1.5, borderColor: Colors.primary, borderRadius: 14, paddingVertical: 16, alignItems: 'center', width: '100%' }}
            >
              <Text style={{ fontSize: 17, fontWeight: '600', color: Colors.primary }}>Skip Now</Text>
            </TouchableOpacity>

          </View>
        </View>
      </Modal>

      {/* 🛠️ DEVELOPER SIMULATION TOOLBAR — ONLY VISIBLE IN TESTING */}
      {params.rideId && devToolsOpen && (
        <View style={{ position: 'absolute', bottom: 100, alignSelf: 'center', backgroundColor: 'rgba(0,0,0,0.8)', padding: 8, borderRadius: 12, flexDirection: 'row', gap: 6, zIndex: 999 }}>
          <View style={{ paddingHorizontal: 8, justifyContent: 'center' }}>
             <Text style={{ color: '#aaa', fontSize: 10, fontWeight: 'bold' }}>SIMULATOR</Text>
             <Text style={{ color: 'white', fontSize: 10 }}>{rideStatus}</Text>
          </View>
          
          {rideStatus === 'SEARCHING' && (
            <TouchableOpacity 
              onPress={async () => {
                try {
                  await api.post(`/rides/${params.rideId}/simulate-action/`, { action: 'ACCEPT' });
                  alert("Accepted by Bot Driver 🤖");
                } catch (err: any) {
                  if (err.response) {
                    // HTTP error — log and show, don't crash
                    console.warn('SimulateAction ACCEPT error:', err.response.status, err.response.data);
                    alert(`Accept failed: ${err.response.data?.error ?? err.response.status}`);
                  } else {
                    // Network error — rethrow
                    throw err;
                  }
                }
              }}
              style={devBtn} 
            >
              <Text style={{ color: 'white', fontSize: 12 }}>Accept</Text>
            </TouchableOpacity>
          )}

          {rideStatus === 'ASSIGNED' && (
            <TouchableOpacity 
              onPress={async () => {
                try {
                  await api.post(`/rides/${params.rideId}/simulate-action/`, { action: 'ARRIVE' });
                  alert("Driver Arrived 📍");
                } catch (err: any) {
                  if (err.response) {
                    console.warn('SimulateAction ARRIVE error:', err.response.status, err.response.data);
                    alert(`Arrive failed: ${err.response.data?.error ?? err.response.status}`);
                  } else {
                    throw err;
                  }
                }
              }}
              style={devBtn}
            >
              <Text style={{ color: 'white', fontSize: 12 }}>Arrive</Text>
            </TouchableOpacity>
          )}

          {rideStatus === 'ARRIVED' && (
            <TouchableOpacity 
              onPress={async () => {
                try {
                  await api.post(`/rides/${params.rideId}/simulate-action/`, { action: 'START' });
                  alert("Ride Started 🚕");
                } catch (err: any) {
                  if (err.response) {
                    console.warn('SimulateAction START error:', err.response.status, err.response.data);
                    alert(`Start failed: ${err.response.data?.error ?? err.response.status}`);
                  } else {
                    throw err;
                  }
                }
              }}
              style={devBtn}
            >
              <Text style={{ color: 'white', fontSize: 12 }}>Start</Text>
            </TouchableOpacity>
          )}

          {rideStatus === 'ONGOING' && (
            <TouchableOpacity 
              onPress={async () => {
                try {
                  await api.post(`/rides/${params.rideId}/simulate-action/`, { action: 'COMPLETE' });
                } catch (err: any) {
                  if (err.response) {
                    console.warn('SimulateAction COMPLETE error:', err.response.status, err.response.data);
                    alert(`Complete failed: ${err.response.data?.error ?? err.response.status}`);
                  } else {
                    throw err;
                  }
                }
              }}
              style={devBtn}
            >
              <Text style={{ color: 'white', fontSize: 12 }}>Complete</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity onPress={() => setDevToolsOpen(false)} style={{ padding: 4 }}>
             <Ionicons name="close-circle" size={16} color="white" />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const devBtn = {
  backgroundColor: '#444',
  paddingHorizontal: 10,
  paddingVertical: 6,
  borderRadius: 6,
  borderWidth: 1,
  borderColor: '#666',
};

const styles = {
  headerBtn: {
    width: 44, height: 44, backgroundColor: Colors.primaryLight, borderRadius: 12,
    alignItems: 'center' as const, justifyContent: 'center' as const,
    shadowColor: Colors.shadow, shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3,
  },
  inputRow: {
    flexDirection: 'row' as const, alignItems: 'center' as const,
    backgroundColor: Colors.white, borderRadius: 12, borderWidth: 1, borderColor: Colors.primaryBorder,
    paddingHorizontal: 12, paddingVertical: 14,
  },
};
