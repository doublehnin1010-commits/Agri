import { useMutation } from "@tanstack/react-query";
import { BookOpenText, Loader2, SendHorizonal } from "lucide-react";
import { FormEvent, useCallback, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { ChatMessages } from "../components/ChatMessages";
import { VoiceButton } from "../components/VoiceButton";
import { useHistory } from "../hooks/useHistory";
import { sendChatMessage } from "../services/chatService";
import type { HistoryMessage } from "../types/history";
import { answerToText, makeId } from "../utils/answer";
import { getConversationTitle } from "../utils/history";

export function ChatPage() {
  const [message, setMessage] = useState("");
  const [isListening, setIsListening] = useState(false);
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

  const { mutate, isPending } = mutation;

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isPending) return;

      const userMessage: HistoryMessage = {
        id: makeId("user"),
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };

      appendMessage(userMessage);
      setMessage("");
      mutate({
        message: trimmed,
        conversationId: currentConversation?.id === "draft" ? undefined : currentConversation?.id,
      });
    },
    [appendMessage, currentConversation?.id, isPending, mutate],
  );

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    sendMessage(message);
  };

  const handleVoiceTranscript = useCallback(
    (transcript: string) => {
      setMessage(transcript);
      sendMessage(transcript);
    },
    [sendMessage],
  );

  const handleNewChat = () => {
    startNewConversation();
    setMessage("");
  };

  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col">
      <div className="border-b border-slate-200 bg-white px-3 py-3 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-bold text-slate-950 sm:text-lg">{title}</h1>
            <p className="text-xs text-slate-500 sm:text-sm">Ask about Myanmar proverbs, meanings, examples, and usage.</p>
          </div>
          <button type="button" onClick={handleNewChat} className="btn-secondary w-full sm:w-auto">
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

      <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white p-3 sm:p-5">
        <div className="mx-auto flex max-w-4xl flex-col gap-2 sm:gap-3">
          <label className="sr-only" htmlFor="chat-message">Message</label>
          <textarea
            id="chat-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={1}
            className="form-input max-h-40 min-h-11 w-full min-w-0 resize-none py-3 sm:min-h-12"
            placeholder="Ask about a Myanmar proverb..."
          />
          <div className="flex items-center justify-between gap-2 sm:justify-end">
            <p className="text-xs text-slate-500 sm:hidden" aria-live="polite">
              {isListening ? "Listening..." : " "}
            </p>
            <div className="ml-auto flex items-center gap-2">
              <VoiceButton
                onTranscript={handleVoiceTranscript}
                onInterimTranscript={setMessage}
                disabled={mutation.isPending}
                onListeningChange={setIsListening}
              />
              <button
                type="submit"
                className="btn-primary h-11 shrink-0 px-4 sm:h-12"
                disabled={!message.trim() || mutation.isPending || isListening}
                aria-label="Send message"
              >
                {mutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <SendHorizonal className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>
      </form>
    </main>
  );
}
