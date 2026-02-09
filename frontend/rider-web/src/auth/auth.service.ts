import http from "../services/http";

export type LoginResponse = {
  access: string;
  refresh: string;
};

export const login = (username: string, password: string) =>
  http.post<LoginResponse>("/users/login/", {
    username,
    password,
  });
