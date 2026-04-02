import { View, Text, Image, TouchableOpacity, Dimensions, FlatList, Animated } from 'react-native';
import React, { useRef, useState, useEffect } from 'react';
import { useRouter } from 'expo-router';
import Svg, { Circle } from 'react-native-svg';
import Colors from '../../constants/Colors';

const { width, height } = Dimensions.get('window');

const SLIDES = [
  {
    key: '1',
    image: require('../../assets/images/on1.gif'),
    title: 'Anywhere you are',
    description: 'Sell houses easily with the help of Listenoryx and to make this line big I am writing more.',
  },
  {
    key: '2',
    image: require('../../assets/images/on2.gif'),
    title: 'At anytime',
    description: 'Sell houses easily with the help of Listenoryx and to make this line big I am writing more.',
  },
  {
    key: '3',
    image: require('../../assets/images/on3.gif'),
    title: 'Book your car',
    description: 'Sell houses easily with the help of Listenoryx and to make this line big I am writing more.',
  },
];

function SlideItem({ item, index, currentIndex }: { item: typeof SLIDES[0]; index: number; currentIndex: number }) {
  const fadeAnim = useRef(new Animated.Value(index === 0 ? 1 : 0)).current;
  const [gifKey, setGifKey] = useState(0);

  useEffect(() => {
    if (currentIndex === index) {
      setGifKey((k) => k + 1); // remount GIF to restart it
      fadeAnim.setValue(0);
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }).start();
    }
  }, [currentIndex]);

  return (
    <View style={{ width, flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View style={{ opacity: fadeAnim, alignItems: 'center' }}>
        <Image
          key={gifKey}
          source={item.image}
          style={{ width: width * 0.8, height: height * 0.4 }}
          resizeMode="contain"
        />
      </Animated.View>

      <Text style={{ fontSize: 28, fontWeight: '800', color: Colors.textDark, textAlign: 'center', marginTop: 24, paddingHorizontal: 32 }}>
        {item.title}
      </Text>

      <Text style={{ fontSize: 16, color: Colors.textMuted, textAlign: 'center', lineHeight: 24, marginTop: 12, paddingHorizontal: 40 }}>
        {item.description}
      </Text>
    </View>
  );
}

const RADIUS = 34;
const STROKE = 4;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const SIZE = (RADIUS + STROKE) * 2;
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

function ProgressButton({ currentIndex, total, onPress, isLast }: {
  currentIndex: number; total: number; onPress: () => void; isLast: boolean;
}) {
  const animVal = useRef(new Animated.Value(currentIndex / (total - 1))).current;

  useEffect(() => {
    Animated.timing(animVal, {
      toValue: (currentIndex + 1) / total,
      duration: 400,
      useNativeDriver: false,
    }).start();
  }, [currentIndex]);

  const strokeDashoffset = animVal.interpolate({
    inputRange: [0, 1],
    outputRange: [CIRCUMFERENCE, 0],
  });

  const AnimatedCircle = Animated.createAnimatedComponent(Circle);
  const cx = SIZE / 2;
  const cy = SIZE / 2;

  return (
    <View style={{ alignItems: 'center', paddingBottom: 48 }}>
      <TouchableOpacity onPress={onPress} style={{ width: SIZE, height: SIZE, alignItems: 'center', justifyContent: 'center' }}>
        <Svg width={SIZE} height={SIZE} style={{ position: 'absolute' }}>
          {/* Track */}
          <Circle
            cx={cx} cy={cy} r={RADIUS}
            stroke="rgba(245,166,35,0.25)" strokeWidth={STROKE} fill="none"
          />
          {/* Progress — rotated via transform so arc starts from top */}
          <AnimatedCircle
            cx={cx} cy={cy} r={RADIUS}
            stroke={Colors.primary}
            strokeWidth={STROKE}
            fill="none"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform={`rotate(-90, ${cx}, ${cy})`}
          />
        </Svg>
        <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: Colors.primary, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={{ fontSize: isLast ? 18 : 26, fontWeight: '700', color: Colors.white }}>
            {isLast ? 'Go' : '→'}
          </Text>
        </View>
      </TouchableOpacity>
    </View>
  );
}

export default function OnboardingScreen() {
  const router = useRouter();
  const flatListRef = useRef<FlatList>(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  const goToWelcome = () => router.replace('/(auth)/welcome');

  const handleNext = () => {
    if (currentIndex < SLIDES.length - 1) {
      const next = currentIndex + 1;
      flatListRef.current?.scrollToIndex({ index: next, animated: true });
      setCurrentIndex(next);
    } else {
      goToWelcome();
    }
  };

  const isLast = currentIndex === SLIDES.length - 1;

  return (
    <View style={{ flex: 1, backgroundColor: Colors.white }}>
      {/* Skip */}
      <TouchableOpacity onPress={goToWelcome} style={{ position: 'absolute', top: 52, right: 24, zIndex: 10 }}>
        <Text style={{ fontSize: 17, color: '#2196F3', fontWeight: '500' }}>Skip</Text>
      </TouchableOpacity>

      <FlatList
        ref={flatListRef}
        data={SLIDES}
        keyExtractor={(item) => item.key}
        horizontal
        pagingEnabled
        scrollEnabled={false}
        showsHorizontalScrollIndicator={false}
        renderItem={({ item, index }) => (
          <SlideItem item={item} index={index} currentIndex={currentIndex} />
        )}
      />

      {/* Next / Go button */}
      <ProgressButton currentIndex={currentIndex} total={SLIDES.length} onPress={handleNext} isLast={isLast} />

    </View>
  );
}
