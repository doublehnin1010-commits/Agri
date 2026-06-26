import { apiClient } from "../api/client";
import type { AiAnswer } from "../types";
import type { HistoryConversation, HistoryMessage, LegacyHistoryItem } from "../types/history";
import { answerToText, makeId } from "../utils/answer";
import { getConversationTitle } from "../utils/history";

type HistoryApiResponse =
  | HistoryConversation[]
  | { items?: Array<HistoryConversation | LegacyHistoryItem> };

export async function fetchHistory(limit = 100): Promise<HistoryConversation[]> {
  const { data } = await apiClient.get<HistoryApiResponse>("/history", { params: { limit } });
  const items = Array.isArray(data) ? data : data.items ?? [];
  return items.map(normalizeConversation);
}

export async function renameHistory(conversationId: string, title: string): Promise<{ id: string; title: string }> {
  const { data } = await apiClient.patch<{ id: string; title: string }>(`/history/${conversationId}`, { title });
  return data;
}

export async function deleteHistory(conversationId: string): Promise<void> {
  await apiClient.delete(`/history/${conversationId}`);
}

function normalizeConversation(item: HistoryConversation | LegacyHistoryItem, index: number): HistoryConversation {
  if ("messages" in item) {
    const conversation = {
      id: String(item.id ?? makeId("history")),
      title: item.title ?? "",
      created_at: item.created_at,
      messages: item.messages.map(normalizeMessage),
    };
    return { ...conversation, title: getConversationTitle(conversation) };
  }

  const createdAt = item.created_at;
  const assistantAnswer = item.assistant_message;
  const conversation = {
    id: item.id ?? `legacy-${createdAt}-${index}`,
    title: item.title ?? item.user_message,
    created_at: createdAt,
    messages: [
      {
        id: makeId("history-user"),
        role: "user" as const,
        content: item.user_message,
        created_at: createdAt,
      },
      {
        id: makeId("history-assistant"),
        role: "assistant" as const,
        content: answerToText(assistantAnswer),
        answer: typeof assistantAnswer === "string" ? undefined : assistantAnswer,
        created_at: createdAt,
      },
    ],
  };
  return { ...conversation, title: getConversationTitle(conversation) };
}

function normalizeMessage(message: HistoryMessage): HistoryMessage {
  const content = message.content || answerToText(message.answer as AiAnswer | undefined);
  return {
    ...message,
    id: message.id ?? makeId(`history-${message.role}`),
    content,
  };
}
