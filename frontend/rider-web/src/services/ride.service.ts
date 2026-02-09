import { api } from "./api";

export async function getActiveRide() {
  const res = await api.get("/rides/active/");
  return res.data; // null or ride
}

export async function createRide(payload: any) {
  const res = await api.post("/rides/", payload);
  return res.data;
}

export async function cancelRide(id: number) {
  await api.post(`/rides/${id}/cancel/`);
}
