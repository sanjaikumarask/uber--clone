import { api } from "./axios";

export async function login(username: string, password: string) {
  const res = await api.post("/api/users/login/", {
    username,
    password,
  });
  return res.data.access as string;
}
