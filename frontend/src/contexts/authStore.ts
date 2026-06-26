import { create } from "zustand";
import type { User, UserRole } from "../types";

const TOKEN_KEY = "mpai.token";
const USER_KEY = "mpai.user";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setSession: (token: string, user: User) => void;
  logout: () => void;
}

function readUser(): User | null {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) ?? "null");
  } catch {
    return null;
  }
}

function decodeJwtRole(token: string): { email?: string; role?: UserRole } {
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? ""));
    return { email: payload.email, role: payload.role };
  } catch {
    return {};
  }
}

export function userFromToken(token: string, role?: UserRole): User {
  const decoded = decodeJwtRole(token);
  return {
    email: decoded.email ?? "user@example.com",
    role: role ?? decoded.role ?? "user",
  };
}

export const useAuthStore = create<AuthState>((set) => {
  const token = localStorage.getItem(TOKEN_KEY);
  const user = readUser();

  return {
    token,
    user,
    isAuthenticated: Boolean(token),
    setSession: (nextToken, nextUser) => {
      localStorage.setItem(TOKEN_KEY, nextToken);
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
      set({ token: nextToken, user: nextUser, isAuthenticated: true });
    },
    logout: () => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      set({ token: null, user: null, isAuthenticated: false });
    },
  };
});
