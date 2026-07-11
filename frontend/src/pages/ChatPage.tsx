import { useMutation } from "@tanstack/react-query";
import { BookOpenText, Loader2, SendHorizonal } from "lucide-react";
import { FormEvent, useCallback, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { ChatMessages } from "../components/ChatMessages";
import { VoiceButton } from "../components/VoiceButton";
import { VoiceStatus } from "../components/VoiceStatus";
import { useHistory } from "../hooks/useHistory";
import { useVoiceConversation } from "../hooks/useVoiceConversation";
import { sendChatMessage } from "../services/chatService";
import type { ChatResponse } from "../services/chatService";
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

  const handleChatResponse = useCallback(
    (response: ChatResponse) => {
      const answerText = answerToText(response.answer);
      appendMessage({
        id: makeId("assistant"),
        role: "assistant",
        content: answerText,
        answer: response.answer,
        created_at: new Date().toISOString(),
      });
      persistCurrentConversation({
        id: response.conversation_id,
        title: response.title,
        created_at: response.created_at,
      });
      return answerText;
    },
    [appendMessage, persistCurrentConversation],
  );

  const mutation = useMutation({
    mutationFn: sendChatMessage,
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const { mutateAsync, isPending } = mutation;

  const sendMessage = useCallback(
    async (text: string): Promise<string | undefined> => {
      const trimmed = text.trim();
      if (!trimmed || isPending) return undefined;

      const userMessage: HistoryMessage = {
        id: makeId("user"),
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };

      appendMessage(userMessage);
      setMessage("");
      const response = await mutateAsync({
        message: trimmed,
        conversationId: currentConversation?.id === "draft" ? undefined : currentConversation?.id,
      });
      return handleChatResponse(response);
    },
    [appendMessage, currentConversation?.id, handleChatResponse, isPending, mutateAsync],
  );

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void sendMessage(message);
  };

  const voice = useVoiceConversation({
    disabled: isPending,
    onTranscript: sendMessage,
  });

  const handleNewChat = () => {
    voice.stopVoiceMode();
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
            <VoiceStatus status={voice.status} audioLevel={voice.audioLevel} />
            <div className="ml-auto flex items-center gap-2">
              <VoiceButton
                isVoiceMode={voice.isVoiceMode}
                status={voice.status}
                isMuted={voice.isMuted}
                canReplay={Boolean(voice.lastSpokenText.trim())}
                disabled={mutation.isPending}
                onToggleVoiceMode={voice.toggleVoiceMode}
                onToggleMute={voice.toggleMute}
                onReplay={voice.replayLastResponse}
                onStopSpeaking={voice.stopSpeaking}
                onExit={voice.stopVoiceMode}
              />
              <button
                type="submit"
                className="btn-primary h-11 shrink-0 px-4 sm:h-12"
                disabled={
                  !message.trim() ||
                  mutation.isPending ||
                  voice.status === "listening" ||
                  voice.status === "recording"
                }
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
