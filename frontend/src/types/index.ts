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
  document_id?: string | null;
  filename?: string | null;
  file_type?: string | null;
  chunk_id?: number | string | null;
  page_number?: number | null;
  source?: string | null;
  preview?: string | null;
  score?: number | null;
  similarity?: number | null;
}

export interface AiAnswer {
  answer?: string | null;
  language?: "my" | "en" | string | null;
  sources?: SourceItem[];
  error?: string | null;
  meaning_simple_mm?: string | null;
  meaning?: string | null;
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  imageUrl?: string;
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
