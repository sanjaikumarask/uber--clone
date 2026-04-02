import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';

export default function PrivacyPolicyScreen() {
  const router = useRouter();

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Privacy Policy</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.textDark, marginBottom: 14 }}>
          Privacy Policy for Ride share
        </Text>
        <Text style={{ fontSize: 15, color: Colors.textDark, lineHeight: 24 }}>
          {'At Rideshare, accessible from rideshare.com, one of our main priorities is the privacy of our visitors. This Privacy Policy document contains types of information that is collected and recorded by rideshare and how we use it.\n'}
          {'If you have additional questions or require more information about our Privacy Policy, do not hesitate to contact us.\n'}
          {'This Privacy Policy applies only to our online activities and is valid for visitors to our website with regards to the information that they shared and/or collect in rideshare. This policy is not applicable to any information collected offline or via channels other than this website. Our Privacy Policy was created with the help of the Free Privacy Policy Generator.'}
        </Text>
      </ScrollView>
    </View>
  );
}
