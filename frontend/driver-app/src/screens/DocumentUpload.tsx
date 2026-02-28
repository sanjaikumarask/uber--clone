// src/screens/DocumentUpload.tsx (driver-app)

import React, { useState, useEffect, useCallback } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Image, ScrollView, Alert, ActivityIndicator } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../services/api";

const DOC_TYPES = [
    { label: "Driving License", value: "LICENSE" },
    { label: "Registration Certificate (RC)", value: "RC" },
    { label: "Insurance Policy", value: "INSURANCE" },
];

export default function DocumentUploadScreen({ navigation }: any) {
    const [uploads, setUploads] = useState<Record<string, { uri?: string, status: string, reason?: string }>>({});
    const [loading, setLoading] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);

    useFocusEffect(
        useCallback(() => {
            fetchDocuments();
        }, [])
    );

    const fetchDocuments = async () => {
        try {
            const { data } = await api.get("/drivers/documents/upload/");
            const mapped: any = {};
            data.forEach((doc: any) => {
                mapped[doc.document_type] = {
                    status: doc.status,
                    reason: doc.rejection_reason,
                    uri: doc.image_url
                };
            });
            setUploads(mapped);
        } catch (err) {
            console.error("Fetch docs error:", err);
        } finally {
            setInitialLoading(false);
        }
    };

    const pickImage = async (type: string) => {
        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ['images'],
            allowsEditing: true,
            aspect: [4, 3],
            quality: 0.8,
        });

        if (!result.canceled) {
            setUploads(prev => ({
                ...prev,
                [type]: { ...prev[type], uri: result.assets[0].uri, status: "DRAFT" }
            }));
        }
    };

    const handleUpload = async (type: string) => {
        const fileUri = uploads[type]?.uri;
        if (!fileUri) return;

        try {
            setLoading(true);
            const formData = new FormData();

            const filename = fileUri.split('/').pop() || 'upload.jpg';
            const match = /\.(\w+)$/.exec(filename);
            const mimeType = match ? `image/${match[1]}` : `image/jpeg`;

            formData.append("document_type", type);
            // @ts-ignore
            formData.append("file", {
                uri: fileUri,
                name: filename,
                type: mimeType,
            });

            await api.post("/drivers/documents/upload/", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });

            setUploads(prev => ({
                ...prev,
                [type]: { ...prev[type], status: "PENDING", reason: "" }
            }));

            Alert.alert("Success", "Document uploaded for verification.");
        } catch (err) {
            console.error("Upload error:", err);
            Alert.alert("Upload Failed", "Could not upload document.");
        } finally {
            setLoading(false);
        }
    };

    if (initialLoading) {
        return (
            <View style={[styles.container, { justifyContent: "center" }]}>
                <ActivityIndicator size="large" color="#000" />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <Text style={styles.backBtn}>← Back</Text>
                </TouchableOpacity>
                <Text style={styles.title}>Verification</Text>
                <View style={{ width: 50 }} />
            </View>

            <ScrollView style={styles.body} contentContainerStyle={{ paddingBottom: 40 }}>
                <Text style={styles.instructions}>
                    Please upload clear photos of the following documents. Our team will verify them within 24-48 hours.
                </Text>

                {DOC_TYPES.map(doc => {
                    const upload = uploads[doc.value];
                    const isApproved = upload?.status === "APPROVED";
                    const isRejected = upload?.status === "REJECTED";
                    const isPending = upload?.status === "PENDING";

                    return (
                        <View key={doc.value} style={[styles.docCard, isApproved && styles.approvedCard, isRejected && styles.rejectedCard]}>
                            <View style={styles.docInfo}>
                                <Text style={styles.docLabel}>{doc.label}</Text>
                                <View style={styles.statusRow}>
                                    {isApproved && <Text style={styles.approvedText}>✅ Approved</Text>}
                                    {isPending && <Text style={styles.pendingText}>⏳ Under Review</Text>}
                                    {isRejected && <Text style={styles.errorText}>❌ Rejected</Text>}
                                </View>
                            </View>

                            {isRejected && upload.reason && (
                                <View style={styles.reasonBox}>
                                    <Text style={styles.reasonTitle}>Reason for rejection:</Text>
                                    <Text style={styles.reasonText}>{upload.reason}</Text>
                                </View>
                            )}

                            {upload?.uri ? (
                                <View>
                                    <Image
                                        source={{ uri: upload.uri }}
                                        style={styles.preview}
                                        onLoadStart={() => console.log(`Loading image for ${doc.value}`)}
                                        onLoadEnd={() => console.log(`Loaded image for ${doc.value}`)}
                                    />
                                    {!isApproved && !isPending && (
                                        <View style={styles.btnRow}>
                                            <TouchableOpacity style={styles.retakeBtn} onPress={() => pickImage(doc.value)}>
                                                <Text style={styles.retakeText}>Change</Text>
                                            </TouchableOpacity>
                                            <TouchableOpacity style={styles.uploadBtn} onPress={() => handleUpload(doc.value)} disabled={loading}>
                                                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.uploadText}>Submit</Text>}
                                            </TouchableOpacity>
                                        </View>
                                    )}
                                </View>
                            ) : (
                                isApproved || isPending ? (
                                    <View style={[styles.preview, { backgroundColor: "#E5E7EB", justifyContent: "center", alignItems: "center" }]}>
                                        <Text style={{ fontSize: 40 }}>📄</Text>
                                        <Text style={{ fontSize: 12, color: "#666", marginTop: 8 }}>Record on File</Text>
                                    </View>
                                ) : (
                                    <TouchableOpacity style={styles.placeholder} onPress={() => pickImage(doc.value)}>
                                        <Text style={styles.placeholderIcon}>📷</Text>
                                        <Text style={styles.placeholderText}>Tap to upload</Text>
                                    </TouchableOpacity>
                                )
                            )}

                            {(isApproved || isPending) && (
                                <View style={styles.lockedState}>
                                    <Text style={styles.lockedText}>Document is locked while {isApproved ? "approved" : "under review"}.</Text>
                                </View>
                            )}
                        </View>
                    );
                })}
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: "#fff", paddingTop: 60 },
    header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 20, marginBottom: 20 },
    backBtn: { fontSize: 16, color: "#007AFF" },
    title: { fontSize: 20, fontWeight: "bold" },
    body: { flex: 1, paddingHorizontal: 20 },
    instructions: { fontSize: 14, color: "#666", lineHeight: 20, marginBottom: 25 },
    docCard: { backgroundColor: "#F9FAFB", borderRadius: 12, padding: 15, marginBottom: 20, borderWidth: 1, borderColor: "#E5E7EB" },
    approvedCard: { borderColor: "#34C759", backgroundColor: "#F2FBF4" },
    rejectedCard: { borderColor: "#FF3B30", backgroundColor: "#FFF5F5" },
    docInfo: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
    docLabel: { fontSize: 16, fontWeight: "600" },
    statusRow: { flexDirection: "row", alignItems: "center" },
    approvedText: { color: "#34C759", fontWeight: "600", fontSize: 13 },
    pendingText: { color: "#FF9500", fontWeight: "600", fontSize: 13 },
    errorText: { color: "#FF3B30", fontWeight: "600", fontSize: 13 },
    reasonBox: { backgroundColor: "#FFE5E5", padding: 10, borderRadius: 8, marginBottom: 15 },
    reasonTitle: { fontSize: 12, fontWeight: "700", color: "#FF3B30", marginBottom: 2 },
    reasonText: { fontSize: 13, color: "#333" },
    lockedState: { marginTop: 10, padding: 10, backgroundColor: "#E5E7EB", borderRadius: 8, alignItems: "center" },
    lockedText: { fontSize: 12, color: "#666", fontStyle: "italic" },
    placeholder: { height: 120, borderStyle: "dashed", borderWidth: 2, borderColor: "#D1D5DB", borderRadius: 8, justifyContent: "center", alignItems: "center", backgroundColor: "#fff" },
    placeholderIcon: { fontSize: 32, marginBottom: 8 },
    placeholderText: { color: "#9CA3AF" },
    preview: { width: "100%", height: 180, borderRadius: 8, marginBottom: 12 },
    btnRow: { flexDirection: "row", gap: 10 },
    retakeBtn: { flex: 1, padding: 12, borderRadius: 8, borderWidth: 1, borderColor: "#D1D5DB", alignItems: "center" },
    retakeText: { fontWeight: "600" },
    uploadBtn: { flex: 1, padding: 12, borderRadius: 8, backgroundColor: "#000", alignItems: "center" },
    uploadText: { color: "#fff", fontWeight: "600" },
});
