# Introduction to the Rider Web Platform

The Rider Web application is the primary desktop portal for users to interact with the platform. It is designed to be highly responsive, informative, and optimized for larger screen real estate.

## Global Objectives

1. **Desktop Accessibility**: Provide a high-quality alternative to the mobile app for users booking from offices or homes.
2. **Information Density**: Leverage larger screen sizes to show more granular ride history, charts, and platform statistics.
3. **Real-time Visibility**: Provide clear, accurate status of active trips with sub-second map synchronization.
4. **Secure Transactions**: Ensure safe and transparent payment handling with standardized web-based gateways.
5. **Clean Aesthetics**: Maintain a premium,"Uber-style"dark mode interface with smooth transitions and layout animations.

## Technical Stack

- **Framework**: React 19 with **Vite** for blazing fast development and build times.
- **Language**: TypeScript for type safety and code quality.
- **Routing**: React Router 6 for declarative navigation and layout management.
- **State Management**: **Zustand** for lightweight, performant global state.
- **Maps**: `@react-google-maps/api` for high-precision map rendering.
- **Charts**: **Recharts** for visualizing ride history and spending trends.

## Core User Flow

1. **Authentication**: Fast login/signup with phone number and JWT persistence.
2. **Discovery**: Interactive map-based destination selection with address autocomplete.
3. **Booking**: Fare comparison, promo code application, and ride request.
4. **Matching**: Real-time waiting screen while the backend assigns a driver.
5. **Journey**: Live tracking of the driver's arrival and the subsequent ride path using WebSockets.
6. **History & Analysis**: Detailed view of past rides with spending trends and rating summaries.
7. **Support**: Centralized ticket management system for ride-related disputes.
