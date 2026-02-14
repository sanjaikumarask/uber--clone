import { api } from "../../services/http";

export type LoginResponse = {
  access: string;
  refresh: string;
  user: {
    id: number;
    phone: string;
    role: "rider" | "driver";
    first_name: string;
    last_name: string;
  };
};

export async function login(
  phone: string,
  password: string
): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/users/login/", {
    phone,
    password,
  });

  return res.data; // ✅ RETURN FULL PAYLOAD
}
