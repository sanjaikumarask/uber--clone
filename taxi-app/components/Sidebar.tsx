import { View, Text, TouchableOpacity, Image, Modal, Dimensions, Animated } from 'react-native';
import React, { useEffect, useRef, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../constants/Colors';

const SCREEN_WIDTH = Dimensions.get('window').width;
const SIDEBAR_WIDTH = SCREEN_WIDTH * 0.65;

type Props = { visible: boolean; onClose: () => void };

const menuItems = [
  { label: 'Edit Profile', icon: 'person-outline' },
  { label: 'Address',      icon: 'location-outline' },
  { label: 'History',      icon: 'document-text-outline' },
  { label: 'Complain',     icon: 'alert-circle-outline' },
  { label: 'Referral',     icon: 'people-outline' },
  { label: 'About Us',     icon: 'information-circle-outline' },
  { label: 'Settings',     icon: 'settings-outline' },
  { label: 'Help and Support', icon: 'help-circle-outline' },
  { label: 'Logout',       icon: 'log-out-outline' },
];

export default function Sidebar({ visible, onClose }: Props) {
  const router = useRouter();
  const slideAnim = useRef(new Animated.Value(-SIDEBAR_WIDTH)).current;
  const [logoutVisible, setLogoutVisible] = useState(false);

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: visible ? 0 : -SIDEBAR_WIDTH,
      duration: 280,
      useNativeDriver: true,
    }).start();
  }, [visible]);

  const handleMenu = (label: string) => {
    onClose();
    if (label === 'Edit Profile') router.push('/(tabs)/profile');
    if (label === 'Address') router.push('/screens/address');
    if (label === 'History') router.push('/screens/history');
    if (label === 'Complain') router.push('/screens/complain');
    if (label === 'Referral') router.push('/screens/referral');
    if (label === 'About Us') router.push('/screens/aboutus');
    if (label === 'Settings') router.push('/screens/settings');
    if (label === 'Help and Support') router.push('/screens/helpsupport');
    if (label === 'Logout') { setLogoutVisible(true); return; }
  };

  return (
    <>
    {/* Logout confirmation modal */}
    <Modal visible={logoutVisible} transparent animationType="fade" onRequestClose={() => setLogoutVisible(false)}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
        <View style={{ backgroundColor: Colors.white, borderRadius: 24, padding: 24, width: '100%' }}>
          {/* Emoji */}
          <Text style={{ fontSize: 72, textAlign: 'center', marginBottom: 16 }}>😓</Text>

          {/* Title */}
          <Text style={{ fontSize: 18, fontWeight: '800', color: Colors.textDark, marginBottom: 8 }}>
            Log out of your account?
          </Text>

          {/* Subtitle */}
          <Text style={{ fontSize: 14, color: Colors.textMuted, lineHeight: 18, marginBottom: 24 }}>
            You'll be signed out of your profile account. You can log back in anytime.
          </Text>

          {/* Buttons */}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 26 }}>
            <TouchableOpacity
              onPress={() => setLogoutVisible(false)}
              style={{ flex: 1, borderWidth: 1.5, borderColor: '#D0D0D0', borderRadius: 10, paddingVertical: 10, alignItems: 'center' }}
            >
              <Text style={{ fontSize: 15, color: Colors.textDark }}>Stay logged in</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => { setLogoutVisible(false); onClose(); router.replace('/(auth)/login'); }}
              style={{ flex: 1, backgroundColor: '#D32F2F', borderRadius: 10, paddingVertical: 10, alignItems: 'center' }}
            >
              <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.white }}>Log out</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>

    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
      {/* Dim overlay */}
      <TouchableOpacity
        activeOpacity={1}
        onPress={onClose}
        style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' }}
      >
        {/* Sidebar panel — stop touch propagation */}
        <Animated.View
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: SIDEBAR_WIDTH,
            backgroundColor: Colors.white,
            borderTopRightRadius: 32,
            borderBottomRightRadius: 32,
            transform: [{ translateX: slideAnim }],
            paddingTop: 52,
            paddingHorizontal: 24,
            paddingBottom: 40,
          }}
        >
          <TouchableOpacity activeOpacity={1}>
            {/* Back button */}
            <TouchableOpacity onPress={onClose} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 28 }}>
              <Ionicons name="chevron-back" size={22} color={Colors.textDark} />
              <Text style={{ fontSize: 17, fontWeight: '600', color: Colors.textDark, marginLeft: 4 }}>Back</Text>
            </TouchableOpacity>

            {/* Profile section */}
            <View style={{ marginBottom: 28 }}>
              <View style={{ position: 'relative', width: 80, marginBottom: 14 }}>
                <View style={{ width: 80, height: 80, borderRadius: 40, borderWidth: 2, borderColor: Colors.primary, overflow: 'hidden' }}>
                  <Image
                    source={require('../assets/images/profile.jpg')}
                    style={{ width: 80, height: 80 }}
                    resizeMode="cover"
                  />
                </View>
                {/* Camera badge */}
                <View style={{
                  position: 'absolute', bottom: 0, right: 0,
                  width: 26, height: 26, borderRadius: 13,
                  backgroundColor: Colors.white,
                  borderWidth: 1.5, borderColor: Colors.primaryBorder,
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <Ionicons name="camera-outline" size={14} color={Colors.textDark} />
                </View>
              </View>
              <Text style={{ fontSize: 22, fontWeight: '700', color: Colors.textDark, marginBottom: 4 }}>Wentrite</Text>
              <Text style={{ fontSize: 14, color: Colors.textMuted }}>wentrite@email.com</Text>
            </View>

            {/* Divider */}
            <View style={{ height: 1, backgroundColor: '#F0F0F0', marginBottom: 8 }} />

            {/* Menu items */}
            {menuItems.map((item, index) => (
              <TouchableOpacity
                key={item.label}
                onPress={() => handleMenu(item.label)}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  paddingVertical: 16,
                  borderBottomWidth: index < menuItems.length - 1 ? 1 : 0,
                  borderBottomColor: '#F0F0F0',
                }}
              >
                <Ionicons name={item.icon as any} size={18} color={Colors.textDark} style={{ marginRight: 16 }} />
                <Text style={{ fontSize: 14, color: Colors.textDark, fontWeight: '500' }}>{item.label}</Text>
              </TouchableOpacity>
            ))}
          </TouchableOpacity>
        </Animated.View>
      </TouchableOpacity>
    </Modal>
    </>  
  );
}
