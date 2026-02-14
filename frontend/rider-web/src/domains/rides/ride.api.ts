import { api } from "../../services/http";

export async function createRide(payload: {
  pickup_lat: number;
  pickup_lng: number;
  drop_lat: number;
  drop_lng: number;
}) {
  const res = await api.post("/rides/create/", payload);
  return res.data;
}

export async function getActiveRide() {
  const res = await api.get("/rides/active/");
  return res.data;
}
