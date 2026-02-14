import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from "react-native";
import { api } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

export default function LoginScreen({ navigation }: any) {
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();

    const handleLogin = async () => {
        if (!phone || !password) {
            Alert.alert("Error", "Please fill all fields");
            return;
        }

        setLoading(true);
        try {
            const endpoint = "/users/login/";
            console.log("Attempting login to:", endpoint);

            const res = await api.post(endpoint, {
                phone,
                password,
            });

            console.log("✅ Login response:", res.data);

            const { access, refresh, user } = res.data;
            if (user.role !== "rider") {
                Alert.alert("Error", "This app is for Riders only");
                return;
            }

            await login(access, refresh, user);
        } catch (err: any) {
            console.error("Login failed", err.response?.data || err.message);
            Alert.alert("Login Failed", err.response?.data?.error || "Invalid credentials");
        } finally {
            setLoading(false);
        }
    };

    return (
        <View style={styles.container}>
            <Text style={styles.title}>Uber Rider</Text>

            <View style={styles.inputContainer}>
                <Text style={styles.label}>Phone Number</Text>
                <TextInput
                    style={styles.input}
                    placeholder="Enter phone number"
                    value={phone}
                    onChangeText={setPhone}
                    keyboardType="phone-pad"
                    autoCapitalize="none"
                />
            </View>

            <View style={styles.inputContainer}>
                <Text style={styles.label}>Password</Text>
                <TextInput
                    style={styles.input}
                    placeholder="Enter password"
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry
                />
            </View>

            <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
                {loading ? (
                    <ActivityIndicator color="#fff" />
                ) : (
                    <Text style={styles.buttonText}>Login</Text>
                )}
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
        fontSize: 32,
        fontWeight: "bold",
        marginBottom: 40,
        textAlign: "center",
    },
    inputContainer: {
        marginBottom: 20,
    },
    label: {
        fontSize: 16,
        fontWeight: "600",
        marginBottom: 8,
        color: "#333",
    },
    input: {
        height: 50,
        borderWidth: 1,
        borderColor: "#ccc",
        borderRadius: 8,
        paddingHorizontal: 15,
        fontSize: 16,
        backgroundColor: "#f9f9f9",
    },
    button: {
        backgroundColor: "#000",
        height: 50,
        borderRadius: 8,
        justifyContent: "center",
        alignItems: "center",
        marginTop: 20,
    },
    buttonText: {
        color: "#fff",
        fontSize: 18,
        fontWeight: "bold",
    },
});
