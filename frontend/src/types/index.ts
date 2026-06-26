export type UserRole = "user" | "admin";

export interface User {
  id?: string;
  name?: string;
  username?: string;
  email: string;
  role: UserRole;
}

export interface AuthResponse {
  access_token?: string;
  token?: string;
  token_type?: string;
  role?: UserRole;
  user?: User;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface SourceItem {
  keyword?: string | null;
  proverb?: string | null;
  meaning?: string | null;
  example?: string | null;
  score?: number | null;
}

export interface AiAnswer {
  proverb?: string | null;
  meaning_simple_mm?: string | null;
  meaning?: string | null;
  example_mm?: string | null;
  example?: string | null;
  sources?: SourceItem[];
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  answer?: AiAnswer;
  createdAt: string;
}

export interface HistoryApiItem {
  user_message: string;
  assistant_message: AiAnswer;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
}

export interface Proverb {
  id: string;
  keyword?: string | null;
  proverb: string;
  meaning?: string | null;
  example?: string | null;
}

export interface ImportResult {
  inserted: number;
  skipped: number;
  warnings: string[];
  collection: string;
}
