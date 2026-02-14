export interface User {
  id: number;
  phone: string;
  role: "RIDER" | "DRIVER";
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}
