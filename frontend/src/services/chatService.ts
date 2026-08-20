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

export async function sendImageChatMessage(payload: {
  image: File;
  question?: string;
  conversationId?: string;
}): Promise<ChatResponse> {
  const formData = new FormData();
  formData.append("image", payload.image, payload.image.name);
  formData.append("question", payload.question ?? "");
  if (payload.conversationId) formData.append("conversation_id", payload.conversationId);
  const { data } = await apiClient.post<ChatResponse>("/chat/image", formData, { timeout: 180_000 });
  return data;
}

export async function getHistory(limit = 100): Promise<HistoryApiItem[]> {
  const { data } = await apiClient.get<{ items?: HistoryApiItem[] } | HistoryApiItem[]>("/history", {
    params: { limit },
  });
  return Array.isArray(data) ? data : data.items ?? [];
}
