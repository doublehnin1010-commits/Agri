import { useAuthStore } from "../contexts/authStore";

export function useAuth() {
  return useAuthStore();
}
