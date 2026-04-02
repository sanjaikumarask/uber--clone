import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, Alert, ActivityIndicator, ScrollView, StatusBar } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../services/api';
import Colors from '../../constants/Colors';

export default function RateDriverScreen() {
    const router = useRouter();
    const params = useLocalSearchParams<{ rideId: string }>();
    const [rating, setRating] = useState(0);
    const [comment, setComment] = useState('');
    const [tipAmount, setTipAmount] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [tipSubmitting, setTipSubmitting] = useState(false);
    const [hasSubmitted, setHasSubmitted] = useState(false);

    const handleAddTip = async (amount: string) => {
        if (!amount || parseFloat(amount) <= 0) return;
        setTipSubmitting(true);
        try {
            await api.post(`/rides/${params.rideId}/tip/`, { tip_amount: amount });
            Alert.alert('Thank You!', `₹${amount} tip sent to driver.`);
            setTipAmount('');
        } catch (err: any) {
            Alert.alert('Error', err.response?.data?.error || 'Failed to add tip.');
        } finally {
            setTipSubmitting(false);
        }
    };

    const handleSubmit = async () => {
        if (rating === 0) {
            Alert.alert('Rating Required', 'Please select a star rating before submitting.');
            return;
        }

        if (submitting || hasSubmitted) return;

        setSubmitting(true);
        try {
            await api.post(`/rides/${params.rideId}/feedback/`, {
                rating,
                comment: comment || 'Great trip!',
            });
            setHasSubmitted(true);
            Alert.alert('Thank You!', 'Your feedback has been submitted.', [
                { text: 'OK', onPress: () => router.replace('/(tabs)') }
            ]);
        } catch (err: any) {
            if (err.response?.status === 400) {
                // If it was already submitted via a race condition or ghost tap, silently succeed and route home
                setHasSubmitted(true);
                router.replace('/(tabs)');
            } else {
                Alert.alert('Error', 'Failed to submit rating.');
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <ScrollView style={{ flex: 1, backgroundColor: Colors.white }} contentContainerStyle={{ padding: 24, paddingBottom: 60 }} showsVerticalScrollIndicator={false}>
            <StatusBar barStyle="dark-content" backgroundColor={Colors.white} />
            
            <Text style={{ fontSize: 32, fontWeight: '900', color: Colors.textDark, marginTop: 48, marginBottom: 8 }}>
                Rate your trip
            </Text>
            <Text style={{ fontSize: 15, color: Colors.textSub, marginBottom: 40 }}>How was your experience?</Text>

            <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 12, marginBottom: 32 }}>
                {[1, 2, 3, 4, 5].map(s => (
                    <TouchableOpacity key={s} onPress={() => setRating(s)} activeOpacity={0.7}>
                        <Text style={{ fontSize: 48, color: rating >= s ? Colors.primary : '#E0E0E0' }}>★</Text>
                    </TouchableOpacity>
                ))}
            </View>

            <TextInput
                style={{ backgroundColor: '#F9F9F9', borderRadius: 16, padding: 18, color: Colors.textDark, fontSize: 15, minHeight: 100, textAlignVertical: 'top', borderWidth: 1, borderColor: '#E5E5E5', marginBottom: 32 }}
                placeholder="Leave a comment..."
                placeholderTextColor={Colors.textPlaceholder}
                value={comment}
                onChangeText={setComment}
                multiline
            />

            <Text style={{ fontSize: 16, fontWeight: '800', color: Colors.textDark, marginBottom: 8 }}>Add a tip</Text>
            <Text style={{ fontSize: 12, color: Colors.textSub, marginBottom: 16 }}>100% goes to your driver</Text>
            <View style={{ flexDirection: 'row', gap: 10, marginBottom: 16 }}>
                {['20', '50', '100'].map(amt => (
                    <TouchableOpacity
                        key={amt}
                        onPress={() => handleAddTip(amt)}
                        disabled={tipSubmitting}
                        style={{ backgroundColor: 'rgba(245, 166, 35, 0.1)', paddingHorizontal: 20, paddingVertical: 12, borderRadius: 12, borderWidth: 1, borderColor: 'rgba(245, 166, 35, 0.2)' }}
                    >
                        <Text style={{ color: Colors.primary, fontWeight: '800' }}>+₹{amt}</Text>
                    </TouchableOpacity>
                ))}
            </View>
            <View style={{ flexDirection: 'row', gap: 10, marginBottom: 32 }}>
                <TextInput
                    style={{ flex: 1, backgroundColor: Colors.white, borderRadius: 12, paddingHorizontal: 16, color: Colors.textDark, fontSize: 14, fontWeight: '600', borderWidth: 1, borderColor: '#E5E5E5' }}
                    placeholder="Custom amount"
                    placeholderTextColor={Colors.textPlaceholder}
                    keyboardType="numeric"
                    value={tipAmount}
                    onChangeText={setTipAmount}
                />
                <TouchableOpacity
                    onPress={() => handleAddTip(tipAmount)}
                    disabled={!tipAmount || tipSubmitting}
                    style={{ backgroundColor: Colors.primary, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 12, justifyContent: 'center', opacity: (!tipAmount || tipSubmitting) ? 0.5 : 1 }}
                >
                    {tipSubmitting ? <ActivityIndicator size="small" color={Colors.white} /> : <Text style={{ color: Colors.white, fontWeight: '900' }}>Tip</Text>}
                </TouchableOpacity>
            </View>

            <TouchableOpacity
                onPress={handleSubmit}
                disabled={submitting}
                style={{ backgroundColor: Colors.primary, paddingVertical: 18, borderRadius: 16, alignItems: 'center', opacity: submitting ? 0.7 : 1, shadowColor: Colors.primary, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 10, elevation: 5 }}
            >
                {submitting ? <ActivityIndicator color={Colors.white} /> : <Text style={{ color: Colors.white, fontWeight: '900', fontSize: 18 }}>Submit & Go Home</Text>}
            </TouchableOpacity>

            <TouchableOpacity onPress={() => router.replace('/(tabs)')} style={{ alignItems: 'center', paddingVertical: 14, marginTop: 10 }}>
                <Text style={{ color: Colors.textSub, fontSize: 15, fontWeight: '600' }}>Skip</Text>
            </TouchableOpacity>
        </ScrollView>
    );
}

