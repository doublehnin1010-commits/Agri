import type { Conversation } from "../types";

const LOCAL_CONVERSATIONS_KEY = "mpai.localConversations";

export function readLocalConversations(): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_CONVERSATIONS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function writeLocalConversations(conversations: Conversation[]) {
  localStorage.setItem(LOCAL_CONVERSATIONS_KEY, JSON.stringify(conversations));
}

export function removeLocalConversation(id: string) {
  writeLocalConversations(readLocalConversations().filter((item) => item.id !== id));
}
