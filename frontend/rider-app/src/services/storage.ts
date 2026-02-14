import AsyncStorage from "@react-native-async-storage/async-storage";

export const Storage = {
    async getToken() {
        return await AsyncStorage.getItem("access");
    },
    async setToken(token: string) {
        await AsyncStorage.setItem("access", token);
    },
    async setRefresh(token: string) {
        await AsyncStorage.setItem("refresh", token);
    },
    async getUser() {
        const user = await AsyncStorage.getItem("user");
        return user ? JSON.parse(user) : null;
    },
    async setUser(user: any) {
        await AsyncStorage.setItem("user", JSON.stringify(user));
    },
    async clear() {
        await AsyncStorage.clear();
    },
};
