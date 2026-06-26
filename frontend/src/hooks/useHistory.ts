import { create } from "zustand";
import { getApiErrorMessage } from "../api/client";
import { fetchHistory } from "../services/historyService";
import type { HistoryConversation, HistoryMessage } from "../types/history";
import { getConversationTitle } from "../utils/history";

interface HistoryState {
  conversationList: HistoryConversation[];
  currentConversation: HistoryConversation | null;
  loading: boolean;
  error: string | null;
  loadHistory: () => Promise<void>;
  refreshHistory: () => Promise<void>;
  selectConversation: (conversation: HistoryConversation) => void;
  startNewConversation: () => void;
  appendMessage: (message: HistoryMessage) => void;
  persistCurrentConversation: (conversation: Pick<HistoryConversation, "id" | "title" | "created_at">) => void;
  renameConversation: (conversationId: string, title: string) => void;
  removeConversation: (conversationId: string) => void;
}

export const useHistory = create<HistoryState>((set, get) => ({
  conversationList: [],
  currentConversation: null,
  loading: false,
  error: null,

  loadHistory: async () => {
    set({ loading: true, error: null });
    try {
      const conversations = await fetchHistory();
      set({ conversationList: conversations, loading: false });
    } catch (error) {
      set({ error: getApiErrorMessage(error), loading: false });
    }
  },

  refreshHistory: async () => {
    try {
      const conversations = await fetchHistory();
      set({ conversationList: conversations, error: null });
    } catch (error) {
      set({ error: getApiErrorMessage(error) });
    }
  },

  selectConversation: (conversation) => {
    set({ currentConversation: conversation });
  },

  startNewConversation: () => {
    set({ currentConversation: null });
  },

  renameConversation: (conversationId, title) => {
    const currentConversation = get().currentConversation;
    const conversationList = get().conversationList.map((conversation) =>
      conversation.id === conversationId ? { ...conversation, title } : conversation,
    );
    let nextCurrentConversation: HistoryConversation | null = currentConversation;
    if (currentConversation && currentConversation.id === conversationId) {
      nextCurrentConversation = { ...currentConversation, title };
    }
    set({ conversationList, currentConversation: nextCurrentConversation });
  },

  removeConversation: (conversationId) => {
    const currentConversation = get().currentConversation;
    const conversationList = get().conversationList.filter((conversation) => conversation.id !== conversationId);
    let nextCurrentConversation: HistoryConversation | null = currentConversation;
    if (currentConversation && currentConversation.id === conversationId) {
      nextCurrentConversation = conversationList[0] ?? null;
    }
    set({ conversationList, currentConversation: nextCurrentConversation });
  },

  appendMessage: (message) => {
    const current = get().currentConversation;
    const createdAt = current?.created_at ?? new Date().toISOString();
    const nextConversation: HistoryConversation = {
      id: current?.id ?? "draft",
      title: current?.title ?? "",
      created_at: createdAt,
      messages: [...(current?.messages ?? []), message],
    };
    nextConversation.title = getConversationTitle(nextConversation);
    set({ currentConversation: nextConversation });
  },

  persistCurrentConversation: (conversation) => {
    const current = get().currentConversation;
    if (!current) return;

    const persistedConversation: HistoryConversation = {
      ...current,
      id: conversation.id,
      title: conversation.title || current.title,
      created_at: conversation.created_at || current.created_at,
    };
    persistedConversation.title = getConversationTitle(persistedConversation);

    const conversationList = get().conversationList.filter(
      (item) => item.id !== conversation.id && item.id !== current.id,
    );

    set({
      currentConversation: persistedConversation,
      conversationList: [persistedConversation, ...conversationList],
    });
  },
}));
