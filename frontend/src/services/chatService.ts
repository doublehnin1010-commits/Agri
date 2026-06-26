import { apiClient } from "../api/client";
import type { AiAnswer, HistoryApiItem } from "../types";

export interface ChatResponse {
  answer: AiAnswer;
  conversation_id: string;
  title: string;
  created_at: string;
}

export async function sendChatMessage(payload: {
  message: string;
  conversationId?: string;
}): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/chat", {
    message: payload.message,
    conversation_id: payload.conversationId,
  });
  return data;
}

export async function getHistory(limit = 100): Promise<HistoryApiItem[]> {
  const { data } = await apiClient.get<{ items?: HistoryApiItem[] } | HistoryApiItem[]>("/history", {
    params: { limit },
  });
  return Array.isArray(data) ? data : data.items ?? [];
}
