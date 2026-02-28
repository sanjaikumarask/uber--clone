// src/domains/rides/ride.api.ts
import { api } from "../../services/http"; // ✅ corrected import

export interface CreateRidePayload {
  pickup_lat: number;
  pickup_lng: number;
  drop_lat: number;
  drop_lng: number;
}

export const createRideRequest = async (payload: CreateRidePayload) => {
  const res = await api.post("/rides/request/", payload);
  return res.data;
};

export const getActiveRide = async () => {
  const res = await api.get("/rides/active/");
  return res.data;
};
