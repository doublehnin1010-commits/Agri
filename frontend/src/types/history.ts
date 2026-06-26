import type { AiAnswer } from "./index";

export type HistoryMessageRole = "user" | "assistant";

export interface HistoryMessage {
  id?: string;
  role: HistoryMessageRole;
  content: string;
  answer?: AiAnswer;
  created_at?: string;
}

export interface HistoryConversation {
  id: string;
  title: string;
  created_at: string;
  messages: HistoryMessage[];
}

export type HistoryGroupKey = "today" | "yesterday" | "previous7Days" | "older";

export interface GroupedHistory {
  key: HistoryGroupKey;
  label: string;
  conversations: HistoryConversation[];
}

export interface LegacyHistoryItem {
  id?: string;
  title?: string;
  user_message: string;
  assistant_message: AiAnswer | string;
  created_at: string;
}
