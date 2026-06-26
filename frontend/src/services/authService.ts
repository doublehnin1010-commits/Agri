import { apiClient } from "../api/client";
import type { AuthResponse, LoginPayload, RegisterPayload, User } from "../types";

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await apiClient.post<User>("/register", {
    name: payload.username,
    email: payload.email,
    password: payload.password,
  });
  return data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>("/login", payload);
  return data;
}
