import { View, Text, Modal, TouchableOpacity } from 'react-native';
import React from 'react';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Path } from 'react-native-svg';
import Colors from '../constants/Colors';

type Props = {
  visible: boolean;
  title: string;
  subtitle: string;
  buttonText?: string;
  onClose: () => void;
  onButton?: () => void;
};

export default function SuccessModal({ visible, title, subtitle, buttonText, onClose, onButton }: Props) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 }}>
        <View style={{ backgroundColor: Colors.white, borderRadius: 28, paddingHorizontal: 24, paddingTop: 20, paddingBottom: 28, width: '100%', alignItems: 'center' }}>

          {/* Close */}
          <TouchableOpacity onPress={onClose} style={{ alignSelf: 'flex-end', marginBottom: 8 }}>
            <Ionicons name="close" size={24} color={Colors.textDark} />
          </TouchableOpacity>

          {/* Scalloped badge */}
          <View style={{ width: 140, height: 140, alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
            <Svg width={140} height={140} viewBox="0 0 180 180">
              <Path
                d="M90 10 C97 10 102 2 109 5 C116 8 117 17 124 21 C131 25 140 22 146 28 C152 34 149 43 153 51 C157 59 166 62 168 71 C170 80 164 87 164 90 C164 93 170 100 168 109 C166 118 157 121 153 129 C149 137 152 146 146 152 C140 158 131 155 124 159 C117 163 116 172 109 175 C102 178 97 170 90 170 C83 170 78 178 71 175 C64 172 63 163 56 159 C49 155 40 158 34 152 C28 146 31 137 27 129 C23 121 14 118 12 109 C10 100 16 93 16 90 C16 87 10 80 12 71 C14 62 23 59 27 51 C31 43 28 34 34 28 C40 22 49 25 56 21 C63 17 64 8 71 5 C78 2 83 10 90 10Z"
                fill="#D6F5E3"
              />
            </Svg>
            <View style={{ position: 'absolute' }}>
              <Ionicons name="checkmark" size={70} color="#27AE60" />
            </View>
          </View>

          {/* Title */}
          <Text style={{ fontSize: 26, fontWeight: '800', color: Colors.textDark, marginBottom: 10, textAlign: 'center' }}>{title}</Text>

          {/* Subtitle */}
          <Text style={{ fontSize: 14, color: Colors.textMuted, textAlign: 'center', lineHeight: 22 }}>
            {subtitle}
          </Text>

          {/* Optional button */}
          {buttonText && onButton && (
            <TouchableOpacity
              onPress={onButton}
              style={{ backgroundColor: Colors.primary, borderRadius: 14, paddingVertical: 14, alignItems: 'center', width: '100%', marginTop: 24 }}
            >
              <Text style={{ fontSize: 18, fontWeight: '700', color: Colors.white }}>{buttonText}</Text>
            </TouchableOpacity>
          )}

        </View>
      </View>
    </Modal>
  );
}
