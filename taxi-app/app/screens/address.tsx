import { View, Text, TouchableOpacity, FlatList, Modal, TextInput, KeyboardAvoidingView, Platform, TouchableWithoutFeedback, Keyboard, Alert } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '../../services/api';
import Colors from '../../constants/Colors';

type Address = { id: string; label: string; address: string };

const STORAGE_KEY = 'user_addresses';

export default function AddressScreen() {
  const router = useRouter();
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<Address | null>(null);
  const [labelText, setLabelText] = useState('');
  const [addressText, setAddressText] = useState('');

  const fetchAddresses = async () => {
    try {
      const res = await api.get('users/addresses/');
      setAddresses(res.data);
    } catch (err) {
      console.error("Fetch addresses error:", err);
    }
  };

  useEffect(() => {
    fetchAddresses();
  }, []);

  const openAdd = () => {
    setEditingItem(null);
    setLabelText('');
    setAddressText('');
    setModalVisible(true);
  };

  const openEdit = (item: Address) => {
    setEditingItem(item);
    setLabelText(item.label);
    setAddressText(item.address);
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    if (!labelText.trim() || !addressText.trim()) {
      Alert.alert('Error', 'Please fill in both fields.');
      return;
    }
    try {
      if (editingItem) {
        await api.put(`users/addresses/${editingItem.id}/`, {
          label: labelText.trim(),
          address: addressText.trim(),
        });
      } else {
        await api.post('users/addresses/', {
          label: labelText.trim(),
          address: addressText.trim(),
        });
      }
      fetchAddresses();
      setModalVisible(false);
    } catch (err) {
      Alert.alert('Error', 'Failed to save address.');
    }
  };

  const handleDelete = (id: string) => {
    Alert.alert('Delete', 'Remove this address?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive', onPress: async () => {
          try {
            await api.delete(`users/addresses/${id}/`);
            fetchAddresses();
          } catch (err) {
            Alert.alert('Error', 'Failed to delete address.');
          }
        }
      },
    ]);
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#F5F5F5' }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12, backgroundColor: '#F5F5F5' }}>
        <TouchableOpacity style={{ position: 'absolute', left: 16 }} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={24} color={Colors.textDark} />
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Address</Text>
      </View>

      {/* List */}
      <FlatList
        data={addresses}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 12, paddingBottom: 120, gap: 12 }}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', marginTop: 60 }}>
            <Ionicons name="location-outline" size={48} color={Colors.textPlaceholder} />
            <Text style={{ marginTop: 12, fontSize: 15, color: Colors.textPlaceholder }}>No addresses yet</Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14, borderRadius: 16, backgroundColor: Colors.white }}>
            <Ionicons name="location-outline" size={26} color={Colors.primary} style={{ marginRight: 12 }} />
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 15, fontWeight: '700', color: Colors.textDark, marginBottom: 2 }}>{item.label}</Text>
              <Text style={{ fontSize: 13, color: Colors.textMuted }} numberOfLines={2}>{item.address}</Text>
            </View>
            <TouchableOpacity onPress={() => openEdit(item)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }} style={{ marginRight: 10 }}>
              <Ionicons name="create-outline" size={22} color={Colors.primary} />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => handleDelete(item.id)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Ionicons name="trash-outline" size={22} color={Colors.removeBtnColor} />
            </TouchableOpacity>
          </View>
        )}
      />

      {/* Add New Address button */}
      <View style={{ paddingHorizontal: 16, paddingBottom: 28, backgroundColor: '#F5F5F5' }}>
        <TouchableOpacity
          style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center' }}
          onPress={openAdd}
        >
          <Text style={{ fontSize: 17, fontWeight: '700', color: Colors.white }}>Add New Address</Text>
        </TouchableOpacity>
      </View>

      {/* Add / Edit Modal */}
      <Modal visible={modalVisible} transparent animationType="slide" onRequestClose={() => setModalVisible(false)}>
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <KeyboardAvoidingView
            style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.45)' }}
            behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          >
            <TouchableWithoutFeedback>
              <View style={{ backgroundColor: Colors.white, borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingHorizontal: 24, paddingTop: 20, paddingBottom: 36 }}>

                {/* Drag handle */}
                <View style={{ alignItems: 'center', marginBottom: 16 }}>
                  <View style={{ width: 48, height: 5, borderRadius: 3, backgroundColor: '#D0D0D0' }} />
                </View>

                {/* Title */}
                <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark, marginBottom: 20 }}>
                  {editingItem ? 'Edit Address' : 'Add New Address'}
                </Text>

                {/* Label input */}
                <Text style={{ fontSize: 13, fontWeight: '600', color: Colors.textMuted, marginBottom: 6 }}>Label</Text>
                <TextInput
                  value={labelText}
                  onChangeText={setLabelText}
                  placeholder="e.g. Home, Office"
                  placeholderTextColor={Colors.textPlaceholder}
                  style={{ borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15, color: Colors.textDark, marginBottom: 14 }}
                />

                {/* Address input */}
                <Text style={{ fontSize: 13, fontWeight: '600', color: Colors.textMuted, marginBottom: 6 }}>Address</Text>
                <TextInput
                  value={addressText}
                  onChangeText={setAddressText}
                  placeholder="Enter full address"
                  placeholderTextColor={Colors.textPlaceholder}
                  multiline
                  textAlignVertical="top"
                  style={{ borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15, color: Colors.textDark, height: 100, marginBottom: 20 }}
                />

                {/* Buttons */}
                <View style={{ flexDirection: 'row', gap: 12 }}>
                  <TouchableOpacity
                    onPress={() => setModalVisible(false)}
                    style={{ flex: 1, borderWidth: 1.5, borderColor: '#D0D0D0', borderRadius: 12, paddingVertical: 14, alignItems: 'center' }}
                  >
                    <Text style={{ fontSize: 16, color: Colors.textDark }}>Cancel</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={handleSubmit}
                    style={{ flex: 1, backgroundColor: Colors.primary, borderRadius: 12, paddingVertical: 14, alignItems: 'center' }}
                  >
                    <Text style={{ fontSize: 16, fontWeight: '700', color: Colors.white }}>
                      {editingItem ? 'Update' : 'Add'}
                    </Text>
                  </TouchableOpacity>
                </View>

              </View>
            </TouchableWithoutFeedback>
          </KeyboardAvoidingView>
        </TouchableWithoutFeedback>
      </Modal>
    </View>
  );
}
