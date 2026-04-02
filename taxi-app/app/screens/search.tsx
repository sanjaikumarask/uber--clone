import { View, Text, TextInput, TouchableOpacity, FlatList, Image, Keyboard, TouchableWithoutFeedback, ActivityIndicator } from 'react-native';
import React, { useState, useRef, useCallback } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';

const GOOGLE_API_KEY = process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY || '';

type Place = {
  id: string;
  name: string;
  address: string;
};

export default function SearchScreen() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Place[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchPlaces = useCallback(async (text: string) => {
    if (text.trim().length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const url = `https://maps.googleapis.com/maps/api/place/autocomplete/json?input=${encodeURIComponent(text)}&key=${GOOGLE_API_KEY}&language=en&types=geocode`;
      const res = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      const json = await res.json();
      console.log('Places API status:', json.status, json.error_message ?? '');
      if (json.status === 'OK' || json.status === 'ZERO_RESULTS') {
        const mapped: Place[] = (json.predictions ?? []).map((p: any) => ({
          id: p.place_id,
          name: p.structured_formatting?.main_text ?? p.description,
          address: p.structured_formatting?.secondary_text ?? p.description,
        }));
        setResults(mapped);
      } else {
        console.warn('Places API error:', json.status, json.error_message);
        setResults([]);
      }
    } catch (e) {
      console.error('Places fetch error:', e);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChangeText = (text: string) => {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchPlaces(text), 400);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    Keyboard.dismiss();
  };

  const showEmpty = query.trim().length > 0 && !loading && results.length === 0;

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <View className="flex-1" style={{ backgroundColor: Colors.white }}>

        {/* Search bar */}
        <View className="px-4 pt-5 pb-3">
          <View
            className="flex-row items-center px-4 py-4 rounded-2xl"
            style={{ backgroundColor: Colors.primaryBg, borderWidth: 1.5, borderColor: Colors.primaryBorderStrong }}
          >
            <Ionicons name="location-outline" size={20} color={Colors.textMuted} style={{ marginRight: 10 }} />
            <TextInput
              value={query}
              onChangeText={handleChangeText}
              placeholder="Search location..."
              placeholderTextColor={Colors.textPlaceholder}
              autoFocus
              className="flex-1 text-base"
              style={{ color: Colors.textDark }}
            />
            {loading ? (
              <ActivityIndicator size="small" color={Colors.primary} />
            ) : query.length > 0 ? (
              <TouchableOpacity onPress={handleClear}>
                <Ionicons name="close" size={20} color={Colors.textMuted} />
              </TouchableOpacity>
            ) : null}
          </View>
        </View>

        {/* Results count row */}
        {query.trim().length > 0 && !loading && results.length > 0 && (
          <View className="flex-row items-center justify-between px-4 pb-3">
            <Text className="text-base font-bold" style={{ color: Colors.textDark }}>
              Results for{' '}
              <Text style={{ color: Colors.primary }}>"{query}"</Text>
            </Text>
            <Text className="text-base font-bold" style={{ color: Colors.primary }}>
              {results.length} found
            </Text>
          </View>
        )}

        {/* Results list */}
        {results.length > 0 && (
          <FlatList
            data={results}
            keyExtractor={(item) => item.id}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ paddingHorizontal: 16 }}
            showsVerticalScrollIndicator={false}
            renderItem={({ item, index }) => {
              const lowerName = item.name.toLowerCase();
              const lowerQuery = query.toLowerCase();
              const matchIdx = lowerName.indexOf(lowerQuery);
              const before = matchIdx >= 0 ? item.name.slice(0, matchIdx) : item.name;
              const match  = matchIdx >= 0 ? item.name.slice(matchIdx, matchIdx + query.length) : '';
              const after  = matchIdx >= 0 ? item.name.slice(matchIdx + query.length) : '';

              return (
                <TouchableOpacity
                  onPress={() => Keyboard.dismiss()}
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    paddingVertical: 14,
                    borderBottomWidth: index < results.length - 1 ? 1 : 0,
                    borderBottomColor: '#F0F0F0',
                  }}
                >
                  {/* Clock icon */}
                  <Ionicons name="time-outline" size={22} color={Colors.textMuted} style={{ marginRight: 14 }} />

                  {/* Name + address */}
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 16, color: Colors.textDark, marginBottom: 3 }}>
                      {before}
                      <Text style={{ fontWeight: '700' }}>{match}</Text>
                      {after}
                    </Text>
                    {item.address ? (
                      <Text style={{ fontSize: 13, color: Colors.textMuted }} numberOfLines={1}>{item.address}</Text>
                    ) : null}
                  </View>
                </TouchableOpacity>
              );
            }}
          />
        )}

        {/* No result state */}
        {showEmpty && (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
            <Image
              source={require('../../assets/images/search.gif')}
              style={{ width: 280, height: 260 }}
              resizeMode="contain"
            />
            <Text className="text-3xl font-bold text-center mt-6 mb-3" style={{ color: Colors.textDark }}>
              Not Found
            </Text>
            <Text className="text-base text-center leading-6" style={{ color: Colors.textMuted }}>
              Sorry, the keyword you entered cannot be found, please check again or search with another keyword
            </Text>
          </View>
        )}

        {/* Initial empty state */}
        {query.trim().length === 0 && (
          <View className="flex-1 items-center justify-center">
            <Ionicons name="search-outline" size={64} color={Colors.textPlaceholder} />
            <Text className="text-base mt-3" style={{ color: Colors.textPlaceholder }}>Search for a location</Text>
          </View>
        )}

      </View>
    </TouchableWithoutFeedback>
  );
}
