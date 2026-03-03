# Introduction to the Drivers Module

The Drivers module is a critical component of the Uber Clone ecosystem, responsible for managing the supply side of the marketplace.

## Global Objectives

1. **Trust & Safety**: Ensure all drivers are vetted, their documents (License, RC) are verified, and their vehicles meet platform standards.
2. **Performance Optimization**: Categorize drivers into levels (Normal -> Pro) to reward consistency and high quality with priority matching.
3. **Real-time Availability**: Maintain an accurate, sub-second view of which drivers are `ONLINE` and available for ride offers.
4. **Reputation Management**: Continuously evaluate driver behavior through Trust Scores, Acceptance Rates, and Rider Feedback.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **GEO Presence**: Redis `GEOSPATIAL` indexes for low-latency proximity queries.
- **Verification Flow**: S3/Local file storage for document uploads and manual/automated approval logic.
- **Scoring Engine**: Asynchronous Celery tasks for calculating trust scores and level progression.

## The Driver Lifecycle

A `Driver` record progresses through several states:
- **Onboarding**: Profile created, documents uploaded.
- **Verification**: Admin reviews documents; if required (License, RC, Insurance) are approved, the driver is marked `is_verified`.
- **Operational**: Once verified, the driver can toggle between `OFFLINE` and `ONLINE`.
- **Engagement**: Drivers receive offers, complete rides, and improve their `Level` and `Trust Score`.
