import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator, ScrollView } from "react-native";
import { api } from "../services/api";

export default function RegisterScreen({ navigation }: any) {
    const [phone, setPhone] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleRegister() {
        if (!phone || !password || !firstName || !lastName) {
            Alert.alert("Error", "Please fill in all required fields");
            return;
        }

        try {
            setLoading(true);
            await api.post(`users/register/`, {
                phone,
                first_name: firstName,
                last_name: lastName,
                email,
                password,
                role: "driver"
            });

            Alert.alert(
                "Success",
                "Registration successful! Please login to continue.",
                [{ text: "OK", onPress: () => navigation.navigate("Login") }]
            );
        } catch (err: any) {
            const errorData = err.response?.data;
            let msg = "Registration failed";
            if (errorData) {
                msg = Object.values(errorData).flat().join("\n") || msg;
            }
            Alert.alert("Error", msg);
        } finally {
            setLoading(false);
        }
    }

    return (
        <ScrollView contentContainerStyle={styles.container}>
            <Text style={styles.title}>Join as Driver</Text>

            <TextInput
                style={styles.input}
                placeholder="First Name *"
                value={firstName}
                onChangeText={setFirstName}
            />
            <TextInput
                style={styles.input}
                placeholder="Last Name *"
                value={lastName}
                onChangeText={setLastName}
            />
            <TextInput
                style={styles.input}
                placeholder="Phone Number *"
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
            />
            <TextInput
                style={styles.input}
                placeholder="Email (Optional)"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
            />
            <TextInput
                style={styles.input}
                placeholder="Password *"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
            />

            <TouchableOpacity style={styles.btn} onPress={handleRegister} disabled={loading}>
                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Sign Up</Text>}
            </TouchableOpacity>

            <TouchableOpacity style={styles.link} onPress={() => navigation.navigate("Login")}>
                <Text style={styles.linkText}>Already have an account? Login</Text>
            </TouchableOpacity>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        justifyContent: "center",
        padding: 24,
        backgroundColor: "#fff",
    },
    title: {
        fontSize: 28,
        fontWeight: "900",
        marginBottom: 32,
        color: "#000",
        textAlign: "center",
    },
    input: {
        borderWidth: 1,
        borderColor: "#E5E7EB",
        padding: 16,
        borderRadius: 12,
        marginBottom: 16,
        fontSize: 16,
        backgroundColor: "#F9FAFB",
    },
    btn: {
        backgroundColor: "#000",
        padding: 18,
        borderRadius: 12,
        alignItems: "center",
        marginTop: 8,
    },
    btnText: {
        color: "#fff",
        fontSize: 16,
        fontWeight: "700",
    },
    link: {
        marginTop: 24,
        alignItems: "center",
    },
    linkText: {
        color: "#4B5563",
        fontSize: 14,
    },
});
