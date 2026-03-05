import React, { useState } from "react";
import {
    View, Text, TextInput, TouchableOpacity, StyleSheet,
    Alert, ActivityIndicator, KeyboardAvoidingView, Platform, StatusBar
} from "react-native";
import { api } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

export default function LoginScreen({ navigation }: any) {
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [phoneFocused, setPhoneFocused] = useState(false);
    const [passFocused, setPassFocused] = useState(false);
    const { login } = useAuth();

    const handleLogin = async () => {
        if (!phone || !password) {
            Alert.alert("Error", "Please fill all fields");
            return;
        }
        setLoading(true);
        try {
            const res = await api.post("users/login/", { phone, password });
            const { access, refresh, user } = res.data;
            if (user.role !== "rider") {
                Alert.alert("Error", "This app is for Riders only");
                return;
            }
            await login(access, refresh, user);
        } catch (err: any) {
            Alert.alert("Login Failed", err.response?.data?.error || "Invalid credentials");
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.root}
            behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
            <StatusBar barStyle="light-content" backgroundColor="#000" />

            {/* Background decoration dots */}
            <View style={styles.bgDot1} />
            <View style={styles.bgDot2} />

            <View style={styles.container}>
                {/* Logo / Brand */}
                <View style={styles.brand}>
                    <Text style={styles.brandText}>
                        Uber<Text style={styles.brandAccent}> RIDER</Text>
                    </Text>
                </View>

                {/* Card */}
                <View style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.title}>Welcome<Text style={styles.titleDot}>.</Text></Text>
                        <Text style={styles.subtitle}>Sign in to start your journey</Text>
                    </View>

                    {/* Phone Input */}
                    <View style={styles.inputGroup}>
                        <TextInput
                            style={[styles.input, phoneFocused && styles.inputFocused]}
                            placeholder="Phone Number"
                            placeholderTextColor="#444"
                            value={phone}
                            onChangeText={setPhone}
                            keyboardType="phone-pad"
                            autoCapitalize="none"
                            onFocus={() => setPhoneFocused(true)}
                            onBlur={() => setPhoneFocused(false)}
                        />
                    </View>

                    {/* Password Input */}
                    <View style={styles.inputGroup}>
                        <TextInput
                            style={[styles.input, passFocused && styles.inputFocused]}
                            placeholder="Password"
                            placeholderTextColor="#444"
                            value={password}
                            onChangeText={setPassword}
                            secureTextEntry
                            onFocus={() => setPassFocused(true)}
                            onBlur={() => setPassFocused(false)}
                        />
                    </View>

                    {/* Sign In Button */}
                    <TouchableOpacity
                        style={[styles.btn, loading && styles.btnDisabled]}
                        onPress={handleLogin}
                        disabled={loading}
                        activeOpacity={0.85}
                    >
                        {loading ? (
                            <ActivityIndicator color="#fff" size="small" />
                        ) : (
                            <Text style={styles.btnText}>Sign In</Text>
                        )}
                    </TouchableOpacity>

                    {/* Footer */}
                    <View style={styles.footer}>
                        <Text style={styles.footerText}>
                            Don't have an account?{" "}
                            <Text style={styles.footerAccent} onPress={() => navigation.navigate("Signup")}>Sign Up</Text>
                        </Text>
                    </View>
                </View>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    root: {
        flex: 1,
        backgroundColor: "#000",
    },
    bgDot1: {
        position: "absolute",
        top: -80,
        right: -80,
        width: 250,
        height: 250,
        borderRadius: 125,
        backgroundColor: "rgba(39,110,241,0.08)",
    },
    bgDot2: {
        position: "absolute",
        bottom: -100,
        left: -60,
        width: 200,
        height: 200,
        borderRadius: 100,
        backgroundColor: "rgba(39,110,241,0.05)",
    },
    container: {
        flex: 1,
        justifyContent: "center",
        paddingHorizontal: 24,
    },
    brand: {
        alignItems: "center",
        marginBottom: 40,
    },
    brandText: {
        fontSize: 22,
        fontWeight: "900",
        color: "#FFFFFF",
        letterSpacing: -0.5,
    },
    brandAccent: {
        color: "#276EF1",
    },
    card: {
        backgroundColor: "rgba(255,255,255,0.05)",
        borderRadius: 24,
        padding: 28,
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
    },
    cardHeader: {
        marginBottom: 32,
    },
    title: {
        fontSize: 48,
        fontWeight: "900",
        color: "#FFFFFF",
        letterSpacing: -2,
        lineHeight: 52,
        marginBottom: 8,
    },
    titleDot: {
        color: "#276EF1",
    },
    subtitle: {
        fontSize: 15,
        color: "#666",
        fontWeight: "500",
    },
    inputGroup: {
        marginBottom: 16,
    },
    input: {
        backgroundColor: "rgba(255,255,255,0.05)",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.1)",
        borderRadius: 14,
        paddingHorizontal: 20,
        paddingVertical: 18,
        fontSize: 16,
        color: "#FFFFFF",
        fontWeight: "500",
    },
    inputFocused: {
        borderColor: "#276EF1",
        backgroundColor: "rgba(39,110,241,0.06)",
    },
    btn: {
        backgroundColor: "#276EF1",
        borderRadius: 14,
        paddingVertical: 18,
        alignItems: "center",
        justifyContent: "center",
        marginTop: 8,
        shadowColor: "#276EF1",
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.4,
        shadowRadius: 16,
        elevation: 10,
    },
    btnDisabled: {
        opacity: 0.7,
    },
    btnText: {
        color: "#FFFFFF",
        fontSize: 18,
        fontWeight: "900",
        letterSpacing: 0.2,
    },
    footer: {
        alignItems: "center",
        marginTop: 28,
    },
    footerText: {
        fontSize: 14,
        color: "#555",
    },
    footerAccent: {
        color: "#276EF1",
        fontWeight: "700",
    },
});
