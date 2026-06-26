import axios, { AxiosError } from "axios";
import { useAuthStore } from "../contexts/authStore";

const baseURL = `${(import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "")}/api/v1`;

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<{ detail?: string; message?: string }>(error)) {
    return (
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      "Something went wrong"
    );
  }
  return error instanceof Error ? error.message : "Something went wrong";
}
