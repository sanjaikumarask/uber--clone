import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api, apiActions } from '../services/api';
import { Alert } from 'react-native';

export type Favourite = { id: string | number; label: string; address: string; latitude?: number; longitude?: number };

type FavouriteContextType = {
  favourites: Favourite[];
  loading: boolean;
  addFavourite: (label: string, address: string) => Promise<void>;
  removeFavourite: (id: string | number) => Promise<void>;
  isFavourite: (address: string) => boolean;
  refresh: () => Promise<void>;
};

const STORAGE_KEY = 'user_favourites_cache';

const FavouriteContext = createContext<FavouriteContextType>({
  favourites: [],
  loading: false,
  addFavourite: async () => {},
  removeFavourite: async () => {},
  isFavourite: () => false,
  refresh: async () => {},
});

export function FavouriteProvider({ children }: { children: React.ReactNode }) {
  const [favourites, setFavourites] = useState<Favourite[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchBackend = async () => {
    try {
      const res = await apiActions.getAddresses();
      const backendItems = res.data.results || res.data;
      const mapped: Favourite[] = backendItems.map((item: any) => ({
        id: item.id,
        label: item.label,
        address: item.address,
        latitude: item.latitude,
        longitude: item.longitude,
      }));
      setFavourites(mapped);
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(mapped));
    } catch (error) {
      console.warn("Backend Fav fetch failed, using cache:", error);
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) setFavourites(JSON.parse(stored));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBackend();
  }, []);

  const addFavourite = async (label: string, address?: string) => {
    // If only one arg, label acts as address
    const finalAddress = address || label;
    const finalLabel = address ? label : "Home"; // Use "Home" as default if only address is provided

    const tempId = Date.now();
    const newItem = { id: tempId, label: finalLabel, address: finalAddress };
    const previousFavs = [...favourites];
    
    // 1. Optimistic Update
    setFavourites([...favourites, newItem]);
    
    try {
      await apiActions.saveAddress({ label: finalLabel, address: finalAddress });
      await fetchBackend(); // Sync with real IDs
    } catch (e: any) {
      // 2. Rollback on failure
      setFavourites(previousFavs);
      Alert.alert("Error", e.response?.data?.error || "Failed to save address to cloud.");
    }
  };

  const removeFavourite = async (id: string | number) => {
    const previousFavs = [...favourites];
    
    // 1. Optimistic Remove
    setFavourites(favourites.filter(f => f.id !== id));
    
    try {
      await apiActions.deleteAddress(id as number);
      await fetchBackend();
    } catch (e) {
      // 2. Rollback on failure
      setFavourites(previousFavs);
      Alert.alert("Error", "Failed to remove saved address.");
    }
  };

  const isFavourite = (address: string) =>
    favourites.some(f => f.address?.toLowerCase() === address?.toLowerCase());

  return (
    <FavouriteContext.Provider value={{ favourites, loading, addFavourite, removeFavourite, isFavourite, refresh: fetchBackend }}>
      {children}
    </FavouriteContext.Provider>
  );
}

export const useFavourite = () => useContext(FavouriteContext);
