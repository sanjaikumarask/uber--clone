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

export async function register(
  firstName: string,
  lastName: string,
  phone: string,
  password: string,
  role: "rider" | "driver" = "rider"
) {
  const res = await api.post("/users/register/", {
    first_name: firstName,
    last_name: lastName,
    phone,
    password,
    role,
  });

  return res.data;
}
