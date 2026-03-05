// src/domains/rides/ride.store.ts
import { create } from "zustand";
import { api } from "../../services/http";

type LatLng = { lat: number; lng: number };

interface CreateRidePayload {
  pickup_lat: number;
  pickup_lng: number;
  pickup_address?: string;
  drop_lat: number;
  drop_lng: number;
  drop_address?: string;
  vehicle_type?: string;
}

interface RideState {
  rideId: number | null;
  status: string | null;
  fare: number | null;
  otpCode: string | null;
  vehicleType: string | null;

  driverLocation: LatLng | null;
  driverPrevLocation: LatLng | null;
  heading: number | null;
  polyline: string | null;
  eta: string | null;
  pickup: LatLng | null;
  pickupAddress: string | null;
  dropoff: LatLng | null;
  dropoffAddress: string | null;
  completedRoute: LatLng[];
  messages: Array<{ sender_id: number; message: string; created_at: string }>;
  trackingStatus: "disconnected" | "connecting" | "connected";

  driver: {
    first_name: string;
    last_name: string;
    phone: string;
    vehicle_model: string;
    vehicle_number: string;
    rating?: number;
  } | null;

  setRideId: (id: number | null) => void;
  setStatus: (status: string | null) => void;
  setFare: (fare: number | null) => void;
  setOtpCode: (otpCode: string | null) => void;
  setPickup: (loc: LatLng | null, address?: string | null) => void;
  setDropoff: (loc: LatLng | null, address?: string | null) => void;
  setPolyline: (polyline: string | null) => void;
  setEta: (eta: string | null) => void;
  setHeading: (heading: number | null) => void;

  setDriverLocation: (lat: number, lng: number) => void;
  setDriver: (driver: RideState["driver"]) => void;
  setVehicleType: (vType: string | null) => void;
  addMessage: (msg: { sender_id: number; message: string; created_at: string }) => void;
  setTrackingStatus: (status: "disconnected" | "connecting" | "connected") => void;

  createRide: (payload: CreateRidePayload) => Promise<{ ride_id: number }>;
  checkActiveRide: () => Promise<{ ride_id?: number } | null>;
  cancelRide: (rideId: number) => Promise<void>;

  reset: () => void;
}

export const useRideStore = create<RideState>((set, get) => ({
  rideId: null,
  status: null,
  fare: null,
  otpCode: null,
  vehicleType: null,
  driverLocation: null,
  driverPrevLocation: null,
  heading: null,
  polyline: null,
  eta: null,
  pickup: null,
  pickupAddress: null,
  dropoff: null,
  dropoffAddress: null,
  completedRoute: [],
  messages: [],
  driver: null,
  trackingStatus: "disconnected",

  setRideId: (id) => set({ rideId: id }),
  setStatus: (status) => set({ status }),
  setFare: (fare) => set({ fare }),
  setOtpCode: (otpCode) => set({ otpCode }),
  setPickup: (loc, address) => set({ pickup: loc, pickupAddress: address }),
  setDropoff: (loc, address) => set({ dropoff: loc, dropoffAddress: address }),
  setPolyline: (polyline) => set({ polyline }),
  setEta: (eta) => set({ eta }),
  setHeading: (heading) => set({ heading }),
  setDriver: (driver) => set({ driver }),
  setVehicleType: (vehicleType) => set({ vehicleType }),
  setTrackingStatus: (trackingStatus) => set({ trackingStatus }),

  setDriverLocation: (lat, lng) =>
    set((state) => ({
      driverPrevLocation: state.driverLocation,
      driverLocation: { lat, lng },
      completedRoute: [...state.completedRoute, { lat, lng }],
    })),

  addMessage: (msg) => set((state) => {
    // Prevent duplicates
    if (state.messages.some(m => m.created_at === msg.created_at && m.sender_id === msg.sender_id)) {
      return state;
    }
    return { messages: [...state.messages, msg] };
  }),

  // CREATE RIDE
  createRide: async (payload) => {
    try {
      const res = await api.post("/rides/request/", payload);
      if (!res.data || !res.data.id) {
        throw new Error("INVALID_RIDE_RESPONSE");
      }
      const ride = res.data;
      set({
        rideId: ride.id,
        status: ride.status,
        otpCode: ride.otp_code,
        pickup: { lat: parseFloat(ride.pickup_lat), lng: parseFloat(ride.pickup_lng) },
        pickupAddress: ride.pickup_address,
        dropoff: { lat: parseFloat(ride.drop_lat), lng: parseFloat(ride.drop_lng) },
        dropoffAddress: ride.drop_address,
        polyline: ride.polyline || ride.planned_route_polyline,
        fare: ride.final_fare || ride.base_fare,
        vehicleType: ride.vehicle_type,
        driver: ride.driver ? {
          first_name: ride.driver.user.first_name,
          last_name: ride.driver.user.last_name,
          phone: ride.driver.user.phone,
          vehicle_model: ride.driver.vehicle_model,
          vehicle_number: ride.driver.vehicle_number,
          rating: 4.8 // Mock rating
        } : null
      });
      return { ride_id: ride.id };
    } catch (error: any) {
      console.error("Create ride failed:", error?.response?.data || error);
      throw error;
    }
  },

  // CHECK ACTIVE RIDE
  checkActiveRide: async () => {
    try {
      const res = await api.get("/rides/active/");
      const ride = res.data;
      if (!ride || !ride.id) {
        return null;
      }
      set({
        rideId: ride.id,
        status: ride.status,
        otpCode: ride.otp_code,
        pickup: { lat: parseFloat(ride.pickup_lat), lng: parseFloat(ride.pickup_lng) },
        pickupAddress: ride.pickup_address,
        dropoff: { lat: parseFloat(ride.drop_lat), lng: parseFloat(ride.drop_lng) },
        dropoffAddress: ride.drop_address,
        polyline: ride.polyline || ride.planned_route_polyline,
        fare: ride.final_fare || ride.base_fare,
        vehicleType: ride.vehicle_type,
        driver: ride.driver ? {
          first_name: ride.driver.user.first_name,
          last_name: ride.driver.user.last_name,
          phone: ride.driver.user.phone,
          vehicle_model: ride.driver.vehicle_model,
          vehicle_number: ride.driver.vehicle_number,
          rating: 4.8 // Mock rating
        } : null
      });
      return { ride_id: ride.id };
    } catch {
      return null;
    }
  },

  // CANCEL RIDE
  cancelRide: async (rideId) => {
    try {
      await api.post(`/rides/${rideId}/cancel/`);
      get().reset();
    } catch (error: any) {
      console.error("Cancel ride failed:", error?.response?.data || error);
      throw error;
    }
  },

  // RESET STORE
  reset: () =>
    set({
      rideId: null,
      status: null,
      fare: null,
      otpCode: null,
      vehicleType: null,
      driverLocation: null,
      driverPrevLocation: null,
      heading: null,
      polyline: null,
      eta: null,
      pickup: null,
      pickupAddress: null,
      dropoff: null,
      dropoffAddress: null,
      completedRoute: [],
      messages: [],
      driver: null,
      trackingStatus: "disconnected",
    }),
}));
