import { View, Text, TouchableOpacity, TextInput, FlatList, ActivityIndicator, Alert, RefreshControl, KeyboardAvoidingView, Platform } from 'react-native';
import React, { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Colors from '../../constants/Colors';
import { api } from '../../services/api';

type Tab = 'new' | 'mytickets';
type Ticket = { id: number; subject: string; status: string; created_at: string; updated_at?: string };

const CATEGORIES = [
  { label: 'Payment Issue', value: 'payment_issue' },
  { label: 'Ride Problem', value: 'ride_problem' },
  { label: 'App Bug', value: 'app_bug' },
  { label: 'Driver Complaint', value: 'driver_complaint' },
  { label: 'Other', value: 'other' },
];

export default function HelpSupportScreen() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>('new');
  
  // New Ticket State
  const [category, setCategory] = useState<string>('ride_problem');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showCategoryPicker, setShowCategoryPicker] = useState(false);

  // My Tickets State
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (activeTab === 'mytickets') {
      fetchTickets();
    }
  }, [activeTab]);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const res = await api.get('/supports/tickets/');
      setTickets(res.data);
    } catch (error: any) {
      Alert.alert('Error', 'Could not load your tickets.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchTickets();
  };

  const handleSubmit = async () => {
    if (!subject.trim() || !description.trim()) {
      Alert.alert('Error', 'Please enter a subject and description.');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post('/supports/tickets/', {
        category,
        subject: subject.trim(),
        description: description.trim(),
      });
      
      Alert.alert('Success', 'Your ticket has been submitted successfully.');
      setSubject('');
      setDescription('');
      setCategory('ride_problem');
      setActiveTab('mytickets'); // Switch tab

    } catch (error: any) {
      Alert.alert('Submission Failed', error.response?.data?.error || 'Could not submit your ticket.');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'open': return '#FF9800'; // Orange
      case 'resolved': return '#4CAF50'; // Green
      case 'closed': return '#9E9E9E'; // Grey
      default: return Colors.primary;
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 12 }}>
        <TouchableOpacity onPress={() => router.back()} style={{ position: 'absolute', left: 16, flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="chevron-back" size={22} color={Colors.textMid} />
          <Text style={{ fontSize: 16, color: Colors.textMid }}>Back</Text>
        </TouchableOpacity>
        <Text style={{ fontSize: 20, fontWeight: '700', color: Colors.textDark }}>Support</Text>
      </View>

      {/* Tabs */}
      <View style={{ flexDirection: 'row', marginHorizontal: 16, marginVertical: 12, backgroundColor: Colors.primaryBg, borderRadius: 12, borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
        <TouchableOpacity 
          onPress={() => setActiveTab('new')}
          style={{ flex: 1, paddingVertical: 10, alignItems: 'center', backgroundColor: activeTab === 'new' ? Colors.primary : 'transparent', borderRadius: 10, margin: 2 }}
        >
          <Text style={{ fontWeight: '600', color: activeTab === 'new' ? Colors.white : Colors.textMuted }}>New Ticket</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          onPress={() => setActiveTab('mytickets')}
          style={{ flex: 1, paddingVertical: 10, alignItems: 'center', backgroundColor: activeTab === 'mytickets' ? Colors.primary : 'transparent', borderRadius: 10, margin: 2 }}
        >
          <Text style={{ fontWeight: '600', color: activeTab === 'mytickets' ? Colors.white : Colors.textMuted }}>My Tickets</Text>
        </TouchableOpacity>
      </View>

      {activeTab === 'new' ? (
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
          <FlatList
            data={[]}
            keyExtractor={() => "dummy"}
            renderItem={() => null}
            ListHeaderComponent={
              <View style={{ paddingHorizontal: 16, paddingTop: 8, gap: 16 }}>
                {/* Category Dropdown (Custom implementation to avoid extra packages) */}
                <View>
                  <Text style={{ fontSize: 14, fontWeight: '600', color: Colors.textDark, marginBottom: 8 }}>Category</Text>
                  <TouchableOpacity 
                    onPress={() => setShowCategoryPicker(!showCategoryPicker)}
                    style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 14, backgroundColor: '#FAFAFA' }}
                  >
                    <Text style={{ fontSize: 16, color: Colors.textDark }}>
                      {CATEGORIES.find(c => c.value === category)?.label}
                    </Text>
                    <Ionicons name={showCategoryPicker ? 'chevron-up' : 'chevron-down'} size={20} color={Colors.textMuted} />
                  </TouchableOpacity>
                  
                  {showCategoryPicker && (
                    <View style={{ marginTop: 8, borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, backgroundColor: Colors.white, overflow: 'hidden' }}>
                      {CATEGORIES.map((cat, index) => (
                        <TouchableOpacity 
                          key={cat.value} 
                          onPress={() => { setCategory(cat.value); setShowCategoryPicker(false); }}
                          style={{ paddingVertical: 14, paddingHorizontal: 16, borderBottomWidth: index === CATEGORIES.length - 1 ? 0 : 1, borderBottomColor: '#F0F0F0' }}
                        >
                          <Text style={{ fontSize: 16, color: category === cat.value ? Colors.primary : Colors.textDark, fontWeight: category === cat.value ? '600' : '400' }}>
                            {cat.label}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  )}
                </View>

                {/* Subject */}
                <View>
                  <Text style={{ fontSize: 14, fontWeight: '600', color: Colors.textDark, marginBottom: 8 }}>Subject</Text>
                  <TextInput
                    value={subject}
                    onChangeText={setSubject}
                    placeholder="Briefly describe the issue"
                    style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, backgroundColor: '#FAFAFA', color: Colors.textDark }}
                  />
                </View>

                {/* Description */}
                <View>
                  <Text style={{ fontSize: 14, fontWeight: '600', color: Colors.textDark, marginBottom: 8 }}>Description</Text>
                  <TextInput
                    value={description}
                    onChangeText={setDescription}
                    placeholder="Provide details about your issue..."
                    multiline
                    numberOfLines={6}
                    textAlignVertical="top"
                    style={{ borderWidth: 1.5, borderColor: Colors.primaryBorder, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, backgroundColor: '#FAFAFA', minHeight: 120, color: Colors.textDark }}
                  />
                </View>

                {/* Submit Button */}
                <TouchableOpacity
                  disabled={submitting}
                  onPress={handleSubmit}
                  style={{ backgroundColor: submitting ? Colors.textPlaceholder : Colors.primary, borderRadius: 12, paddingVertical: 16, alignItems: 'center', marginTop: 12 }}
                >
                  {submitting ? <ActivityIndicator color={Colors.white} /> : <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>Submit Ticket</Text>}
                </TouchableOpacity>
              </View>
            }
          />
        </KeyboardAvoidingView>
      ) : (
        <View style={{ flex: 1 }}>
          {loading && !refreshing ? (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
              <ActivityIndicator size="large" color={Colors.primary} />
            </View>
          ) : (
            <FlatList
              data={tickets}
              keyExtractor={(item) => item.id.toString()}
              contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 40, paddingTop: 8 }}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
              ListEmptyComponent={
                <View style={{ alignItems: 'center', marginTop: 60 }}>
                  <Ionicons name="documents-outline" size={64} color="#E0E0E0" />
                  <Text style={{ marginTop: 16, fontSize: 16, color: Colors.textMuted }}>No tickets raised yet.</Text>
                </View>
              }
              renderItem={({ item }) => (
                <View style={{ borderRadius: 16, padding: 16, marginBottom: 12, backgroundColor: Colors.white, borderWidth: 1.5, borderColor: Colors.primaryBorder }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <Text style={{ flex: 1, fontSize: 16, fontWeight: '700', color: Colors.textDark, marginRight: 8 }} numberOfLines={2}>
                      {item.subject}
                    </Text>
                    <View style={{ backgroundColor: `${getStatusColor(item.status)}15`, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 }}>
                      <Text style={{ color: getStatusColor(item.status), fontSize: 12, fontWeight: '700', textTransform: 'capitalize' }}>
                        {item.status}
                      </Text>
                    </View>
                  </View>
                  <Text style={{ fontSize: 13, color: Colors.textMuted }}>
                    {new Date(item.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })} • ID: #{item.id}
                  </Text>
                </View>
              )}
            />
          )}
        </View>
      )}
    </View>
  );
}
