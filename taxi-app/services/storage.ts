import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

let SecureStore: any;
let isSecureStoreAvailable = false;

try {
  SecureStore = require("expo-secure-store");
  isSecureStoreAvailable = true;
} catch (error) {
  console.warn("⚠️ Native SecureStore module missing. Falling back silently to AsyncStorage.", error);
  isSecureStoreAvailable = false;
}

const TOKEN_KEY = "Tripzo_access_token";
const REFRESH_TOKEN_KEY = "Tripzo_refresh_token";
const USER_DATA_KEY = "Tripzo_user_data";

export const Storage = {

    async getToken() {
        if (Platform.OS === 'web' || !isSecureStoreAvailable) return AsyncStorage.getItem(TOKEN_KEY);
        try {
            return await SecureStore.getItemAsync(TOKEN_KEY);
        } catch (e) {
            console.warn("SecureStore error, falling back", e);
            return AsyncStorage.getItem(TOKEN_KEY);
        }
    },

    async setToken(token: string) {
        if (Platform.OS === 'web' || !isSecureStoreAvailable) return AsyncStorage.setItem(TOKEN_KEY, token);
        try {
            return await SecureStore.setItemAsync(TOKEN_KEY, token);
        } catch (e) {
            return AsyncStorage.setItem(TOKEN_KEY, token);
        }
    },

    async getRefreshToken() {
        if (Platform.OS === 'web' || !isSecureStoreAvailable) return AsyncStorage.getItem(REFRESH_TOKEN_KEY);
        try {
            return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
        } catch (e) {
            return AsyncStorage.getItem(REFRESH_TOKEN_KEY);
        }
    },

    async setRefreshToken(token: string) {
        if (Platform.OS === 'web' || !isSecureStoreAvailable) return AsyncStorage.setItem(REFRESH_TOKEN_KEY, token);
        try {
            return await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
        } catch (e) {
            return AsyncStorage.setItem(REFRESH_TOKEN_KEY, token);
        }
    },

    async setUserData(data: object) {
        return AsyncStorage.setItem(USER_DATA_KEY, JSON.stringify(data));
    },

    async getUserData() {
        const data = await AsyncStorage.getItem(USER_DATA_KEY);
        return data ? JSON.parse(data) : null;
    },

    async clear() {
        if (Platform.OS === 'web' || !isSecureStoreAvailable) {
            await AsyncStorage.removeItem(TOKEN_KEY);
            await AsyncStorage.removeItem(REFRESH_TOKEN_KEY);
        } else {
            try {
                await SecureStore.deleteItemAsync(TOKEN_KEY);
                await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
            } catch (e) {}
        }
        await AsyncStorage.removeItem(USER_DATA_KEY);
    }
};
