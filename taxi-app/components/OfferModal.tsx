import { View, Text, Modal, TouchableOpacity, ScrollView, Alert } from 'react-native';
import React from 'react';
import { MaterialCommunityIcons, Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Clipboard from 'expo-clipboard';
import Colors from '../constants/Colors';

type Offer = {
  id: string;
  title: string;
  description: string;
  iconColorKey: keyof typeof Colors;
  code: string;
  terms: string[];
};

type Props = {
  offer: Offer | null;
  onClose: () => void;
};

export default function OfferModal({ offer, onClose }: Props) {
  const handleCopy = async (code: string) => {
    await Clipboard.setStringAsync(code);
    Alert.alert('Copied!', `Code "${code}" copied to clipboard.`);
  };

  return (
    <Modal visible={!!offer} transparent animationType="slide" onRequestClose={onClose}>
      <TouchableOpacity activeOpacity={1} onPress={onClose} style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' }}>
        <TouchableOpacity activeOpacity={1} onPress={() => {}} style={{ backgroundColor: Colors.white, borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingBottom: 30 }}>
          {/* Drag handle */}
          <View style={{ alignItems: 'center', paddingTop: 12, paddingBottom: 4 }}>
            <View style={{ width: 48, height: 5, borderRadius: 3, backgroundColor: '#D0D0D0' }} />
          </View>

          {/* Close button */}
          <TouchableOpacity onPress={onClose} style={{ position: 'absolute', top: 16, right: 16, zIndex: 10 }}>
            <Ionicons name="close" size={26} color={Colors.textDark} />
          </TouchableOpacity>

          {/* Title */}
          <Text style={{ textAlign: 'center', fontSize: 20, fontWeight: '700', color: Colors.textDark, paddingTop: 8, paddingBottom: 16 }}>
            Special Offer
          </Text>

          {/* Divider */}
          <View style={{ height: 1, backgroundColor: '#F0F0F0' }} />

          <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 18, paddingBottom: 12 }} showsVerticalScrollIndicator={false}>
            {/* Icon */}
            <View style={{ alignItems: 'center', marginBottom: 14 }}>
              <MaterialCommunityIcons name="tag-outline" size={80} color={Colors.primary} />
            </View>

            {/* Offer title & description */}
            <Text style={{ textAlign: 'center', fontSize: 24, fontWeight: '800', color: Colors.textDark, marginBottom: 6 }}>
              {offer?.title}
            </Text>
            <Text style={{ textAlign: 'center', fontSize: 14, color: Colors.textMuted, marginBottom: 16 }}>
              {offer?.description}
            </Text>

            {/* Coupon code */}
            <TouchableOpacity
              onPress={() => offer && handleCopy(offer.code)}
              style={{ borderRadius: 10, overflow: 'hidden', marginBottom: 18, alignSelf: 'center', width: '55%' }}
            >
              <LinearGradient
                colors={['#F5A623', '#FEF3C7']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, paddingHorizontal: 24, gap: 10 }}
              >
                <Text style={{ fontSize: 18, fontWeight: '800', color: Colors.textDark, letterSpacing: 2 }}>
                  {offer?.code}
                </Text>
                <Ionicons name="copy-outline" size={20} color={Colors.textDark} />
              </LinearGradient>
            </TouchableOpacity>

            {/* Dashed divider */}
            <View style={{ borderTopWidth: 1.5, borderColor: Colors.primaryBorder, borderStyle: 'dashed', marginBottom: 14 }} />

            {/* Terms */}
            <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.textDark, marginBottom: 10 }}>
              Terms and Conditions
            </Text>
            {offer?.terms.map((term, i) => (
              <View key={i} style={{ flexDirection: 'row', marginBottom: 8, gap: 8 }}>
                <Text style={{ color: Colors.textMuted, fontSize: 13, lineHeight: 21 }}>{'\u2022'}</Text>
                <Text style={{ flex: 1, color: Colors.textMuted, fontSize: 13, lineHeight: 21 }}>{term}</Text>
              </View>
            ))}
          </ScrollView>

          {/* Use Promo button */}
          <View style={{ paddingHorizontal: 24, paddingTop: 4 }}>
            <TouchableOpacity
              onPress={() => { onClose(); Alert.alert('Promo Applied!', `Code "${offer?.code}" applied.`); }}
              style={{ backgroundColor: Colors.primary, borderRadius: 16, paddingVertical: 17, alignItems: 'center' }}
            >
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Use Promo</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </TouchableOpacity>
    </Modal>
  );
}
