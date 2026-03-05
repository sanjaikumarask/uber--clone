import { create } from "zustand";

interface RideState {
    rideId: number | null;
    status: string | null;
    socketStatus: "disconnected" | "connecting" | "connected";
    locationSocketStatus: "disconnected" | "connecting" | "connected";

    setRideId: (id: number | null) => void;
    setStatus: (status: string | null) => void;
    setSocketStatus: (status: "disconnected" | "connecting" | "connected") => void;
    setLocationSocketStatus: (status: "disconnected" | "connecting" | "connected") => void;

    reset: () => void;
}

export const useRideStore = create<RideState>((set) => ({
    rideId: null,
    status: null,
    socketStatus: "disconnected",
    locationSocketStatus: "disconnected",

    setRideId: (id) => set({ rideId: id }),
    setStatus: (status) => set({ status }),
    setSocketStatus: (status) => set({ socketStatus: status }),
    setLocationSocketStatus: (status) => set({ locationSocketStatus: status }),

    reset: () => set({
        rideId: null,
        status: null,
        socketStatus: "disconnected",
        locationSocketStatus: "disconnected",
    }),
}));
