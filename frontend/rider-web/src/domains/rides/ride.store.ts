import { create } from "zustand";
import { api } from "../../services/http";

export type RideStatus =
  | "SEARCHING"
  | "OFFERED"
  | "ASSIGNED"
  | "ARRIVED"
  | "ONGOING"
  | "COMPLETED"
  | "CANCELLED";

interface RideState {
  rideId: number | null;
  status: RideStatus | null;
  driverLocation: { lat: number; lng: number } | null;

  createRide: (payload: {
    pickup_lat: number;
    pickup_lng: number;
    drop_lat: number;
    drop_lng: number;
  }) => Promise<void>;

  checkActiveRide: () => Promise<{ ride_id: number | null; status: RideStatus | null }>;

  setStatus: (status: RideStatus) => void;
  setDriverLocation: (lat: number, lng: number) => void;
  reset: () => void;
}

export const useRideStore = create<RideState>((set) => ({
  rideId: null,
  status: null,
  driverLocation: null,

  async createRide(payload) {
    try {
      const { data } = await api.post("/rides/request/", payload);
      set({
        rideId: data.ride_id,
        status: data.status,
      });
    } catch (err: any) {
      if (err.response?.status === 409) {
        throw new Error("ACTIVE_RIDE_EXISTS");
      }
      throw new Error("Ride creation failed");
    }
  },

  async checkActiveRide() {
    const { data } = await api.get("/rides/active/");
    set({
      rideId: data.ride_id ?? null,
      status: data.status ?? null,
    });
    return data;
  },

  setStatus(status) {
    set({ status });
  },

  setDriverLocation(lat, lng) {
    set({ driverLocation: { lat, lng } });
  },

  reset() {
    set({ rideId: null, status: null, driverLocation: null });
  },
}));
