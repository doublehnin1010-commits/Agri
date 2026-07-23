import { useMutation } from "@tanstack/react-query";
import { Loader2, MessageSquarePlus, Mic, SendHorizonal, Volume2, X } from "lucide-react";
import { FormEvent, KeyboardEvent, useCallback, useMemo, useState } from "react";
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
  const [lastAnswerText, setLastAnswerText] = useState("");
  const { currentConversation, appendMessage, persistCurrentConversation, startNewConversation } = useHistory();

  const messages = currentConversation?.messages ?? [];
  const title = useMemo(
    () => (currentConversation ? getConversationTitle(currentConversation) : "New chat"),
    [currentConversation],
  );

  const handleChatResponse = useCallback(
    (response: ChatResponse) => {
      const answerText = answerToText(response.answer);
      setLastAnswerText(answerText);
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

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (message.trim() && !isPending) void sendMessage(message);
    }
  };

  const voice = useVoiceConversation({
    disabled: isPending,
    onTranscript: sendMessage,
  });
  const isMobileVoiceCapture = voice.status === "listening" || voice.status === "recording";
  const canListenToAnswer = Boolean(lastAnswerText.trim());
  const isVoiceBusy =
    voice.status === "uploading" ||
    voice.status === "transcribing" ||
    voice.status === "thinking" ||
    voice.status === "listening" ||
    voice.status === "recording";

  const handleNewChat = () => {
    voice.stopVoiceMode();
    startNewConversation();
    setMessage("");
  };

  return (
    <main className="flex h-[calc(100vh-3.5rem)] min-h-0 flex-col bg-cream">
      <header className="border-b border-slate-100 bg-white px-4 py-2.5 sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold text-slate-900 sm:text-base">{title}</h1>
          </div>
          <button
            type="button"
            onClick={handleNewChat}
            className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-4 focus:ring-slate-100"
            aria-label="Start a new chat"
          >
            <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">New chat</span>
          </button>
        </div>
      </header>

      <section className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:py-8">
        <ChatMessages messages={messages} isResponding={mutation.isPending} onStarterClick={(text) => sendMessage(text)} />
      </section>

      <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white/95 px-3 py-2.5 sm:px-4">
        <div className="mx-auto max-w-4xl">
          <div className="rounded-lg border border-slate-300 bg-white px-3 py-2 shadow-sm focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100">
            <label className="sr-only" htmlFor="chat-message">
              Message
            </label>
            {isMobileVoiceCapture ? (
              <div className="mb-2 flex min-h-11 items-center gap-3 rounded-lg bg-red-50 px-3 py-2 text-red-700 sm:hidden">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100">
                  <Mic className="h-4 w-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold">Recording</p>
                  <p className="truncate text-xs font-medium text-red-500">Tap the mic button to stop</p>
                </div>
                <VoiceStatus status={voice.status} audioLevel={voice.audioLevel} compact />
              </div>
            ) : null}

            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <textarea
                id="chat-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                rows={1}
                className={`max-h-28 min-h-10 flex-1 resize-none border-0 bg-transparent px-0 py-2 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400 sm:min-h-9 ${
                  isMobileVoiceCapture ? "hidden sm:block" : ""
                }`}
                placeholder="Ask about a Myanmar proverb"
              />
              <div className="flex shrink-0 items-center justify-between gap-2 sm:justify-end">
                <div className={isMobileVoiceCapture ? "hidden sm:block" : ""}>
                  <VoiceStatus status={voice.status} audioLevel={voice.audioLevel} />
                </div>
                <div className="ml-auto flex items-center gap-1.5">
                  {canListenToAnswer && !isMobileVoiceCapture ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (voice.status === "speaking") voice.stopSpeaking();
                        else voice.speakResponse(lastAnswerText);
                      }}
                      disabled={mutation.isPending || isVoiceBusy}
                      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50 ${
                        voice.status === "speaking"
                          ? "border-red-300 bg-red-50 text-red-600 focus:ring-red-100"
                          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 focus:ring-brand-100"
                      }`}
                      aria-label={voice.status === "speaking" ? "Stop voice playback" : "Listen to answer"}
                      title={voice.status === "speaking" ? "Stop voice playback" : "Listen to answer"}
                    >
                      {voice.status === "speaking" ? <X className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
                    </button>
                  ) : null}
                  <VoiceButton
                    isVoiceMode={voice.isVoiceMode}
                    status={voice.status}
                    isMuted={voice.isMuted}
                    canReplay={Boolean(voice.lastSpokenText.trim())}
                    language={voice.language}
                    disabled={mutation.isPending}
                    onToggleVoiceMode={voice.toggleVoiceMode}
                    onToggleMute={voice.toggleMute}
                    onReplay={voice.replayLastResponse}
                    onStopSpeaking={voice.stopSpeaking}
                    onExit={voice.stopVoiceMode}
                    onLanguageChange={voice.setLanguage}
                  />
                  <button
                    type="submit"
                    className="btn-primary h-10 w-10 shrink-0 p-0"
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
          </div>
          <p className="mt-1.5 hidden text-center text-[11px] text-slate-400 sm:block">Press Enter to send · Shift + Enter for a new line</p>
        </div>
      </form>
    </main>
  );
}
