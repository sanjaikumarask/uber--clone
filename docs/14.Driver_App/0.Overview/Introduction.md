# Introduction to the Driver App

The Driver App is the operational tool for the supply-side of the Uber Clone platform. It is designed with safety, reliability, and income transparency as the primary focuses.

## Global Objectives

1. **Reliability**: Ensure the app continues to function and stream coordinates even when network connectivity fluctuates or the app is backgrounded.
2. **Safety First**: Large touch targets, minimal required reading, and quick actions to minimize distraction while driving.
3. **Revenue Transparency**: Give drivers clear, real-time views into their daily earnings, pending payouts, and active incentive progress.
4. **Operational Efficiency**: Streamlined document uploading and onboarding so drivers can get on the road faster.

## Technical Stack

- **Framework**: React Native with **Expo** for rapid cross-platform development.
- **Language**: TypeScript for type safety and stability in production.
- **Navigation**: React Navigation 7 (Native Node Stack).
- **State Management**: **Zustand** for lightweight, predictable global state without Redux boilerplate.
- **Media & Sensors**: 
- `expo-av` for distinct audio alerts.
- `expo-image-picker` for document handling.
- `expo-location` for persistent, high-accuracy GPS tracking.

## Core User Flow

1. **Onboarding**: Registration and strict document upload workflow.
2. **Shift Management**: Toggling `ONLINE` / `OFFLINE` status.
3. **Dispatch**: Receiving high-priority audio alerts and visual prompts for new ride offers.
4. **Fulfillment**: Transitioning through `ACCEPTED`, `ARRIVED`, `STARTED`, and `COMPLETED`.
5. **Post-Ride**: Reviewing fare earnings, rating the rider, and returning to `ONLINE` status.
6. **Withdrawal**: Checking the Wallet and initiating backend payouts to a registered bank account.
