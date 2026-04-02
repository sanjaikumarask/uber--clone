import { View, Text, Modal, TouchableOpacity, TextInput, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator, Keyboard } from 'react-native';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../constants/Colors';

import { api } from '../services/api';

const GOOGLE_API_KEY = process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY || '';
 
type Suggestion = { id: string; name: string; address: string };
type Place = { id: string; name: string; address: string; distance: string };

type Props = {
  visible: boolean;
  onClose: () => void;
  currentAddress?: string;
  currentLocation?: { latitude: number; longitude: number };
};

export default function SelectAddressModal({ visible, onClose, currentAddress = '', currentLocation }: Props) {
  const router = useRouter();
  const [fromText, setFromText] = useState(currentAddress);
  const [toText, setToText] = useState('');
  const [recentPlaces, setRecentPlaces] = useState<Place[]>([]);
  
  const [fromSuggestions, setFromSuggestions] = useState<Suggestion[]>([]);
  const [toSuggestions, setToSuggestions] = useState<Suggestion[]>([]);
  const [fromLoading, setFromLoading] = useState(false);
  const [toLoading, setToLoading] = useState(false);
  const [activeField, setActiveField] = useState<'from' | 'to' | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null);

  const fromDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchRecentPlaces = async () => {
    try {
      const res = await api.get('/users/addresses/');
      const data = res.data.results || res.data;
      setRecentPlaces(data.map((item: any) => ({
        id: item.id.toString(),
        name: item.title || item.label || 'Saved Place',
        address: item.address,
        distance: item.distance || 'Saved' 
      })));
    } catch (error) {
      console.warn("Failed to fetch saved addresses:", error);
      // Fallback or leave empty
    }
  };

  useEffect(() => {
    if (visible) {
      setFromText(currentAddress);
      setFromSuggestions([]);
      setToSuggestions([]);
      setActiveField(null);
      fetchRecentPlaces();
    }
  }, [visible, currentAddress]);

  const fetchSuggestions = useCallback(async (
    text: string,
    setLoading: (v: boolean) => void,
    setSuggestions: (v: Suggestion[]) => void
  ) => {
    if (text.trim().length < 2) { setSuggestions([]); return; }
    setLoading(true);
    try {
      const url = `https://maps.googleapis.com/maps/api/place/autocomplete/json?input=${encodeURIComponent(text)}&key=${GOOGLE_API_KEY}&language=en&types=geocode`;
      const res = await fetch(url);
      const json = await res.json();
      if (json.status === 'OK') {
        setSuggestions(json.predictions.map((p: any) => ({
          id: p.place_id,
          name: p.structured_formatting?.main_text ?? p.description,
          address: p.structured_formatting?.secondary_text ?? '',
        })));
      } else {
        // 🔥 MOCK MODE: Provide fallback locations if API Key is invalid
        const mocks: Suggestion[] = [
          { id: 'm1', name: 'Marina Beach 🏖️', address: 'Chennai, Tamil Nadu' },
          { id: 'm2', name: 'Chennai Central 🚉', address: 'Kannappar Thidal, Periyamet' },
          { id: 'm3', name: 'Phoenix Marketcity 🛍️', address: 'Velachery, Chennai' },
          { id: 'm4', name: 'Chennai Airport ✈️', address: 'Meenambakkam, Chennai' },
          { id: 'm5', name: 'T Nagar Bus Stand 🚌', address: 'Usman Road, Chennai' },
        ];
        const filtered = mocks.filter(m => m.name.toLowerCase().includes(text.toLowerCase()));
        setSuggestions(filtered);
      }
    } catch {
      // Catch network errors and still show mocks
      const mocks: Suggestion[] = [
        { id: 'm1', name: 'Marina Beach (Mock) 🏖️', address: 'Chennai, Tamil Nadu' },
        { id: 'm2', name: 'Chennai Central (Mock) 🚉', address: 'Periyamet, Chennai' },
      ];
      setSuggestions(mocks.filter(m => m.name.includes(text)));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFromChange = (text: string) => {
    setFromText(text);
    setActiveField('from');
    if (fromDebounce.current) clearTimeout(fromDebounce.current);
    fromDebounce.current = setTimeout(() => fetchSuggestions(text, setFromLoading, setFromSuggestions), 400);
  };

  const handleToChange = (text: string) => {
    setToText(text);
    setActiveField('to');
    if (toDebounce.current) clearTimeout(toDebounce.current);
    toDebounce.current = setTimeout(() => fetchSuggestions(text, setToLoading, setToSuggestions), 400);
  };

  const fetchDetails = async (placeId: string) => {
    try {
      const url = `https://maps.googleapis.com/maps/api/place/details/json?place_id=${placeId}&key=${GOOGLE_API_KEY}&fields=geometry`;
      const res = await fetch(url);
      const json = await res.json();
      if (json.status === 'OK') {
        return json.result.geometry.location; // { lat, lng }
      }
      // Return mock coordinates for Chennai Central if API fails
      return { lat: 13.0827, lng: 80.2707 };
    } catch (e) {
      console.error('Details fetch error:', e);
      return { lat: 13.0827, lng: 80.2707 };
    }
  };

  const selectFromSuggestion = (item: Suggestion) => {
    setFromText(item.name);
    setFromSuggestions([]);
    setActiveField(null);
  };

  const selectToSuggestion = (item: Suggestion) => {
    setToText(item.name);
    setToSuggestions([]);
    setSelectedPlace({ id: item.id, name: item.name, address: item.address, distance: '' });
    setActiveField(null);
  };

  const handleSelectRecentPlace = (item: Place) => {
    setSelectedPlace(item);
    setToText(item.name);
    setToSuggestions([]);
  };

  const handleClose = () => {
    setSelectedPlace(null);
    setToText('');
    setFromSuggestions([]);
    setToSuggestions([]);
    setActiveField(null);
    onClose();
  };

  const handleConfirm = async () => {
    if (!selectedPlace) return;
    // For saved addresses, we might already have coordinates or we use the name to search
    let latLng = null;
    if (selectedPlace.id.length > 10) { // Likely a Google Place ID
       latLng = await fetchDetails(selectedPlace.id);
    }
    
    handleClose();
    router.push({
        pathname: '/screens/selecttransport',
        params: {
            destName: selectedPlace.name,
            destAddress: selectedPlace.address,
            destLat: latLng?.lat,
            destLng: latLng?.lng,
            pickupLat: currentLocation?.latitude,
            pickupLng: currentLocation?.longitude,
            pickupAddress: currentAddress,
        }
    });
  };

  const SuggestionList = ({ suggestions, onSelect, loading }: {
    suggestions: Suggestion[];
    onSelect: (item: Suggestion) => void;
    loading: boolean;
  }) => {
    if (loading) return (
      <View style={{ paddingVertical: 10, alignItems: 'center' }}>
        <ActivityIndicator size="small" color={Colors.primary} />
      </View>
    );
    if (suggestions.length === 0) return null;
    return (
      <View style={{ backgroundColor: Colors.white, borderRadius: 12, borderWidth: 1, borderColor: Colors.primaryBorder, marginTop: 4, marginHorizontal: 20, overflow: 'hidden' }}>
        {suggestions.map((item, index) => (
          <TouchableOpacity
            key={item.id}
            onPress={() => onSelect(item)}
            style={{
              flexDirection: 'row', alignItems: 'center',
              paddingHorizontal: 14, paddingVertical: 12,
              borderBottomWidth: index < suggestions.length - 1 ? 1 : 0,
              borderBottomColor: '#F0F0F0',
            }}
          >
            <Ionicons name="location-outline" size={18} color={Colors.primary} style={{ marginRight: 10 }} />
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 14, fontWeight: '600', color: Colors.textDark }} numberOfLines={1}>{item.name}</Text>
              {item.address ? <Text style={{ fontSize: 12, color: Colors.textMuted }} numberOfLines={1}>{item.address}</Text> : null}
            </View>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={handleClose}>
      <KeyboardAvoidingView
        style={{ flex: 1, justifyContent: 'flex-end' }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        <TouchableOpacity activeOpacity={1} onPress={handleClose}
          style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }}
        />
        <TouchableOpacity activeOpacity={1} onPress={() => Keyboard.dismiss()}>
          <View style={{ backgroundColor: Colors.white, borderTopLeftRadius: 28, borderTopRightRadius: 28 }}>

            {/* Header — always fixed, never moves with keyboard */}
            <View style={{ alignItems: 'center', paddingTop: 12, paddingBottom: 8 }}>
              <View style={{ width: 48, height: 5, borderRadius: 3, backgroundColor: '#D0D0D0' }} />
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20, paddingBottom: 16 }}>
              <Text style={{ fontSize: 22, fontWeight: '700', color: Colors.textDark }}>Select address</Text>
              <TouchableOpacity onPress={handleClose} style={{ position: 'absolute', right: 20 }}>
                <Ionicons name="close" size={26} color={Colors.textDark} />
              </TouchableOpacity>
            </View>
            <View style={{ height: 1, backgroundColor: '#F0F0F0' }} />

            {/* Scrollable body */}
            <ScrollView
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
              contentContainerStyle={{ paddingBottom: 32 }}
            >

            {/* ── CONFIRMED STATE ── */}
            {selectedPlace && toSuggestions.length === 0 && activeField !== 'to' ? (
              <View style={{ paddingHorizontal: 20, paddingTop: 20 }}>
                <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
                  <View style={{ alignItems: 'center', marginRight: 14 }}>
                    <Ionicons name="location" size={28} color="#E53935" />
                    <View style={{ width: 2, height: 32, borderStyle: 'dashed', borderWidth: 1, borderColor: Colors.primary, marginVertical: 2 }} />
                  </View>
                  <View style={{ flex: 1, paddingTop: 2 }}>
                    <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, marginBottom: 4 }}>Current location</Text>
                    <Text style={{ fontSize: 14, color: Colors.textMuted }}>{fromText || currentAddress}</Text>
                  </View>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'flex-start', marginTop: 8, marginBottom: 32 }}>
                  <Ionicons name="location" size={28} color={Colors.primary} style={{ marginRight: 14 }} />
                  <View style={{ flex: 1, paddingTop: 2 }}>
                    <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, marginBottom: 4 }}>{selectedPlace.name}</Text>
                    <Text style={{ fontSize: 14, color: Colors.textMuted }}>{selectedPlace.address}</Text>
                  </View>
                </View>
                <TouchableOpacity
                  onPress={handleConfirm}
                  style={{ backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 14, alignItems: 'center' }}
                >
                  <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Confirm Location</Text>
                </TouchableOpacity>
              </View>

            ) : (
              /* ── SELECT STATE ── */
              <View style={{ paddingTop: 20 }}>
                {/* From input + suggestions */}
                <View style={{ paddingHorizontal: 20, marginBottom: 4 }}>
                  <View style={inputBox}>
                    <MaterialCommunityIcons name="crosshairs-gps" size={22} color={Colors.primary} style={{ marginRight: 12 }} />
                    <TextInput
                      value={fromText}
                      onChangeText={handleFromChange}
                      onFocus={() => setActiveField('from')}
                      placeholder="From (current location)"
                      placeholderTextColor={Colors.textPlaceholder}
                      style={{ flex: 1, fontSize: 15, color: Colors.textDark }}
                    />
                    {fromLoading
                      ? <ActivityIndicator size="small" color={Colors.primary} />
                      : fromText.length > 0
                        ? <TouchableOpacity onPress={() => { setFromText(''); setFromSuggestions([]); }}>
                            <Ionicons name="close-circle" size={18} color={Colors.textMuted} />
                          </TouchableOpacity>
                        : null
                    }
                  </View>
                </View>

                {/* From suggestions dropdown */}
                {activeField === 'from' && (
                  <SuggestionList suggestions={fromSuggestions} onSelect={selectFromSuggestion} loading={fromLoading} />
                )}

                {/* To input + suggestions */}
                <View style={{ paddingHorizontal: 20, marginTop: 14, marginBottom: 4 }}>
                  <View style={inputBox}>
                    <Ionicons name="location-outline" size={22} color={Colors.textMuted} style={{ marginRight: 12 }} />
                    <TextInput
                      value={toText}
                      onChangeText={handleToChange}
                      onFocus={() => setActiveField('to')}
                      placeholder="To"
                      placeholderTextColor={Colors.textPlaceholder}
                      style={{ flex: 1, fontSize: 15, color: Colors.textDark }}
                    />
                    {toLoading
                      ? <ActivityIndicator size="small" color={Colors.primary} />
                      : toText.length > 0
                        ? <TouchableOpacity onPress={() => { setToText(''); setToSuggestions([]); setSelectedPlace(null); }}>
                            <Ionicons name="close-circle" size={18} color={Colors.textMuted} />
                          </TouchableOpacity>
                        : null
                    }
                  </View>
                </View>

                {/* To suggestions dropdown */}
                {activeField === 'to' && (
                  <SuggestionList suggestions={toSuggestions} onSelect={selectToSuggestion} loading={toLoading} />
                )}

                {/* Recent places — hide when suggestions are showing */}
                {fromSuggestions.length === 0 && toSuggestions.length === 0 && !fromLoading && !toLoading && recentPlaces.length > 0 && (
                  <>
                    <View style={{ height: 1, backgroundColor: '#F0F0F0', marginTop: 16, marginBottom: 16 }} />
                    <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, paddingHorizontal: 20, marginBottom: 8 }}>
                      Recent places
                    </Text>
                    <ScrollView showsVerticalScrollIndicator={false} style={{ maxHeight: 220 }} keyboardShouldPersistTaps="handled">
                      {recentPlaces.map((item, index, arr) => (
                        <TouchableOpacity
                          key={item.id}
                          onPress={() => handleSelectRecentPlace(item)}
                          style={{
                            flexDirection: 'row', alignItems: 'center',
                            paddingHorizontal: 20, paddingVertical: 14,
                            borderBottomWidth: index < arr.length - 1 ? 1 : 0,
                            borderBottomColor: '#F5F5F5',
                          }}
                        >
                          <Ionicons name="location" size={26} color={Colors.textDark} style={{ marginRight: 14 }} />
                          <View style={{ flex: 1 }}>
                            <Text style={{ fontSize: 17, fontWeight: '600', color: Colors.textDark, marginBottom: 3 }}>{item.name}</Text>
                            <Text style={{ fontSize: 13, color: Colors.textMuted }} numberOfLines={1}>{item.address}</Text>
                          </View>
                          <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.textDark, marginLeft: 8 }}>{item.distance}</Text>
                        </TouchableOpacity>
                      ))}
                    </ScrollView>
                  </>
                )}
              </View>
            )}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const inputBox = {
  flexDirection: 'row' as const,
  alignItems: 'center' as const,
  borderWidth: 1.5,
  borderColor: '#D0D0D0',
  borderRadius: 14,
  paddingHorizontal: 16,
  paddingVertical: 16,
  backgroundColor: '#FFFFFF',
};
