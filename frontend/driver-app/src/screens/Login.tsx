import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from "react-native";
import { useAuthStore } from "../domains/auth/auth.store";
import { api } from "../services/api";

export default function LoginScreen() {
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const login = useAuthStore((s) => s.login);

    async function handleLogin() {
        if (!phone || !password) {
            Alert.alert("Error", "Please fill in all fields");
            return;
        }

        try {
            setLoading(true);
            console.log("🔐 Attempting login...");
            console.log("📞 Phone:", phone);
            console.log("🌐 API URL:", api.defaults.baseURL);

            const { data } = await api.post("/users/driver-login/", {
                phone,
                password,
            });

            console.log("✅ Login response received:", JSON.stringify(data, null, 2));

            // Validate response structure
            if (!data.access || !data.refresh || !data.user) {
                console.error("❌ Invalid response structure:", data);
                Alert.alert("Error", "Invalid server response");
                return;
            }

            console.log("💾 Saving auth data...");
            await login(data.user, data.access, data.refresh);
            console.log("✅ Login successful!");

        } catch (err: any) {
            console.error("❌ Login error:", err);
            console.error("❌ Error response:", err.response?.data);
            console.error("❌ Error status:", err.response?.status);
            console.error("❌ Error message:", err.message);

            let errorMessage = "Login failed";

            if (err.response) {
                // Server responded with error
                const data = err.response.data;
                errorMessage = data?.non_field_errors?.[0]
                    || data?.detail
                    || data?.error
                    || `Server error: ${err.response.status}`;
            } else if (err.request) {
                // Request made but no response
                errorMessage = "Cannot reach server. Check your network connection and ensure backend is running.";
            } else {
                // Something else happened
                errorMessage = err.message || "Unknown error occurred";
            }

            Alert.alert("Login Failed", errorMessage);
        } finally {
            setLoading(false);
        }
    }

    return (
        <View style={styles.container}>
            <Text style={styles.title}>Driver Login</Text>

            <TextInput
                style={styles.input}
                placeholder="Phone Number"
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
                autoCapitalize="none"
            />

            <TextInput
                style={styles.input}
                placeholder="Password"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
            />

            <TouchableOpacity style={styles.btn} onPress={handleLogin} disabled={loading}>
                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Login</Text>}
            </TouchableOpacity>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: "center",
        padding: 20,
        backgroundColor: "#fff",
    },
    title: {
        fontSize: 24,
        fontWeight: "bold",
        marginBottom: 20,
        textAlign: "center",
    },
    input: {
        borderWidth: 1,
        borderColor: "#ddd",
        padding: 15,
        borderRadius: 8,
        marginBottom: 15,
        fontSize: 16,
    },
    btn: {
        backgroundColor: "black",
        padding: 15,
        borderRadius: 8,
        alignItems: "center",
    },
    btnText: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "600",
    },
});
