import { View, Text, TextInput, TouchableOpacity, ScrollView, Alert, TouchableWithoutFeedback, Keyboard, KeyboardAvoidingView } from 'react-native';
import React, { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';

export default function ContactUsScreen() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const { api } = require('../../services/api');

  const handleSend = async () => {
    if (!name.trim() || !email.trim() || !message.trim()) {
      Alert.alert('Error', 'Please fill in all required fields.');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post('supports/tickets/general/', {
        category: 'other',
        subject: `Contact Request from ${name}`,
        description: `Name: ${name}\nEmail: ${email}\nPhone: ${phone}\n\nMessage:\n${message}`,
      });
      
      Alert.alert('Sent', 'Your message has been sent successfully. We will contact you soon.');
      setName(''); setEmail(''); setPhone(''); setMessage('');
      router.back();
    } catch (error: any) {
      Alert.alert('Error', 'Failed to send message. Please try again later.');
    } finally {
      setSubmitting(false);
    }
  };


  const inputStyle = {
    borderWidth: 1, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 16, paddingVertical: 18,
    fontSize: 16, color: Colors.textDark, backgroundColor: Colors.white,
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: Colors.white }} behavior="padding">
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <View style={{ flex: 1 }}>
          {/* Header */}
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
            <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
              <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
              <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
            </TouchableOpacity>
            <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Contact Us</Text>
          </View>

          <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 32 }} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
            {/* Title */}
            <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 20 }}>
              Contact us for Ride share
            </Text>

            {/* Address block */}
            <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 8 }}>Address</Text>
            <Text style={{ fontSize: 14, color: Colors.textMuted, textAlign: 'center', lineHeight: 22, marginBottom: 12 }}>
              House# 72, Road# 21, Banani, Velachery-600042 (near Banani Bidyaniketon School & College, beside University of Chennai )
            </Text>
            <Text style={{ fontSize: 14, color: Colors.textMuted, textAlign: 'center', lineHeight: 24, marginBottom: 28 }}>
              {'Call : 13301 (24/7)\nEmail : support@Tripzo.com'}
            </Text>

            {/* Send Message title */}
            <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, textAlign: 'center', marginBottom: 16 }}>
              Send Message
            </Text>

            {/* Form */}
            <View style={{ gap: 12 }}>
              <TextInput value={name} onChangeText={setName} placeholder="Name" placeholderTextColor={Colors.textMuted} style={inputStyle} />
              <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor={Colors.textMuted} keyboardType="email-address" autoCapitalize="none" style={inputStyle} />
              <TextInput value={phone} onChangeText={setPhone} placeholder="Phone Number" placeholderTextColor={Colors.textMuted} keyboardType="phone-pad" style={inputStyle} />
              <TextInput
                value={message} onChangeText={setMessage}
                placeholder="Write your text"
                placeholderTextColor={Colors.textMuted}
                multiline textAlignVertical="top"
                style={[inputStyle, { height: 140 }]}
              />
            </View>

            {/* Send Message button inside scroll */}
            <TouchableOpacity onPress={handleSend} style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center', marginTop: 24 }}>
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Send Message</Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}
