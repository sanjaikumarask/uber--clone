import AsyncStorage from "@react-native-async-storage/async-storage";

export const Storage = {
    setToken: async (token: string) => {
        await AsyncStorage.setItem("access_token", token);
    },
    getToken: async () => {
        return await AsyncStorage.getItem("access_token");
    },
    removeToken: async () => {
        await AsyncStorage.removeItem("access_token");
    },
    setRefreshToken: async (token: string) => {
        await AsyncStorage.setItem("refresh_token", token);
    },
    getRefreshToken: async () => {
        return await AsyncStorage.getItem("refresh_token");
    },
    removeRefreshToken: async () => {
        await AsyncStorage.removeItem("refresh_token");
    },
    clear: async () => {
        await AsyncStorage.clear();
    },
};
