import { useMutation } from "@tanstack/react-query";
import { BookOpenText, Loader2, SendHorizonal } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { ChatMessages } from "../components/ChatMessages";
import { useHistory } from "../hooks/useHistory";
import { sendChatMessage } from "../services/chatService";
import type { HistoryMessage } from "../types/history";
import { answerToText, makeId } from "../utils/answer";
import { getConversationTitle } from "../utils/history";

export function ChatPage() {
  const [message, setMessage] = useState("");
  const {
    currentConversation,
    appendMessage,
    persistCurrentConversation,
    startNewConversation,
  } = useHistory();

  const messages = currentConversation?.messages ?? [];
  const title = useMemo(
    () => (currentConversation ? getConversationTitle(currentConversation) : "New chat"),
    [currentConversation],
  );

  const mutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: async (response) => {
      appendMessage({
        id: makeId("assistant"),
        role: "assistant",
        content: answerToText(response.answer),
        answer: response.answer,
        created_at: new Date().toISOString(),
      });
      persistCurrentConversation({
        id: response.conversation_id,
        title: response.title,
        created_at: response.created_at,
      });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || mutation.isPending) return;

    const userMessage: HistoryMessage = {
      id: makeId("user"),
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    appendMessage(userMessage);
    setMessage("");
    mutation.mutate({
      message: trimmed,
      conversationId: currentConversation?.id === "draft" ? undefined : currentConversation?.id,
    });
  };

  const handleNewChat = () => {
    startNewConversation();
    setMessage("");
  };

  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col">
      <div className="border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-lg font-bold text-slate-950">{title}</h1>
            <p className="text-sm text-slate-500">Ask about Myanmar proverbs, meanings, examples, and usage.</p>
          </div>
          <button type="button" onClick={handleNewChat} className="btn-secondary">
            <BookOpenText className="h-4 w-4" aria-hidden="true" />
            New Chat
          </button>
        </div>
      </div>

      <section className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <ChatMessages
          messages={messages}
          isResponding={mutation.isPending}
          onStarterClick={setMessage}
        />
      </section>

      <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white p-4 sm:p-5">
        <div className="mx-auto flex max-w-4xl items-end gap-3">
          <label className="sr-only" htmlFor="chat-message">Message</label>
          <textarea
            id="chat-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={1}
            className="form-input max-h-40 min-h-12 resize-none py-3"
            placeholder="Ask about a Myanmar proverb..."
          />
          <button type="submit" className="btn-primary h-12 px-4" disabled={!message.trim() || mutation.isPending} aria-label="Send message">
            {mutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <SendHorizonal className="h-5 w-5" />}
          </button>
        </div>
      </form>
    </main>
  );
}
