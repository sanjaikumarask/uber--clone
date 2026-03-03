# Introduction to the Rider App

The Rider App is the primary touchpoint for users to interact with the platform on mobile devices. It is designed to be highly responsive, intuitive, and reliable.

## Global Objectives

1. **Seamless Booking**: Minimize friction from app launch to ride request.
2. **Real-time Visibility**: Provide clear, accurate status of driver proximity and trip progress.
3. **Secure Transactions**: Ensure safe and transparent payment handling.
4. **User Safety**: Integrate specialized safety features (SOS) accessible at any point during a ride.
5. **Cross-Platform Consistency**: Maintain a premium experience across both iOS and Android devices.

## Technical Stack

- **Framework**: React Native with **Expo** for rapid development and OTA updates.
- **Language**: TypeScript for type safety and code quality.
- **Navigation**: React Navigation 7 (Stack and Native support).
- **Animations**: React Native Reanimated for smooth, high-performance interactions.
- **Maps**: React Native Maps integrated with Google Maps SDK.
- **Payments**: Razorpay Native SDK for secure credit card and UPI handling.

## Core User Flow

1. **Authentication**: Fast login/signup with phone number and JWT persistence.
2. **Discovery**: Automatic current location detection and"suggested"destinations.
3. **Booking**: Fare comparison, promo code application, and ride request.
4. **Matching**: Real-time waiting screen while the backend assigns a driver.
5. **Journey**: Live tracking of the driver's arrival and the subsequent ride path.
6. **Conclusion**: Payment settlement, rating, and receipt history.
