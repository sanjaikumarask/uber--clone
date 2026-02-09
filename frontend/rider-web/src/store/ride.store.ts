import { create } from "zustand";

export type RideStatus =
  | "SEARCHING"
  | "ASSIGNED"
  | "ARRIVED"
  | "ONGOING"
  | "COMPLETED"
  | "CANCELLED"
  | null;

interface RideState {
  rideId: number | null;
  status: RideStatus;
  driverLocation?: { lat: number; lng: number };
  prevDriverLocation?: { lat: number; lng: number };

  setRide: (id: number, status: RideStatus) => void;
  updateStatus: (status: RideStatus) => void;
  updateDriverLocation: (lat: number, lng: number) => void;
  clear: () => void;
}

export const useRideStore = create<RideState>((set) => ({
  rideId: null,
  status: null,

  setRide: (id, status) => set({ rideId: id, status }),

  updateStatus: (status) => set({ status }),

  updateDriverLocation: (lat, lng) =>
    set((state) => ({
      prevDriverLocation: state.driverLocation,
      driverLocation: { lat, lng },
    })),

  clear: () =>
    set({
      rideId: null,
      status: null,
      driverLocation: undefined,
      prevDriverLocation: undefined,
    }),
}));
