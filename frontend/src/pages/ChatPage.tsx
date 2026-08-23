import { useMutation } from "@tanstack/react-query";
import { ImagePlus, Loader2, MessageSquarePlus, Mic, SendHorizonal, Volume2, X } from "lucide-react";
import { FormEvent, KeyboardEvent, useCallback, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { ChatMessages } from "../components/ChatMessages";
import { VoiceButton } from "../components/VoiceButton";
import { VoiceStatus } from "../components/VoiceStatus";
import { useHistory } from "../hooks/useHistory";
import { useVoiceConversation } from "../hooks/useVoiceConversation";
import { sendChatMessage, sendImageChatMessage } from "../services/chatService";
import type { ChatResponse } from "../services/chatService";
import type { HistoryMessage } from "../types/history";
import { answerToText, makeId } from "../utils/answer";
import { getConversationTitle } from "../utils/history";

export function ChatPage() {
  const [message, setMessage] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const [lastAnswerText, setLastAnswerText] = useState("");
  const { currentConversation, appendMessage, persistCurrentConversation, startNewConversation } = useHistory();

  const messages = currentConversation?.messages ?? [];
  const title = useMemo(
    () => (currentConversation ? getConversationTitle(currentConversation) : "Ask your first question"),
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
    mutationFn: async (payload: { message: string; conversationId?: string; image?: File }) => {
      if (payload.image) return sendImageChatMessage({ image: payload.image, question: payload.message, conversationId: payload.conversationId });
      return sendChatMessage({ message: payload.message, conversationId: payload.conversationId });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const { mutateAsync, isPending } = mutation;

  const sendMessage = useCallback(
    async (text: string, selectedImage = imageFile): Promise<string | undefined> => {
      const trimmed = text.trim();
      if ((!trimmed && !selectedImage) || isPending) return undefined;
      const displayText = trimmed || "Please analyze this agriculture image.";

      const userMessage: HistoryMessage = {
        id: makeId("user"),
        role: "user",
        content: selectedImage ? `[Image attached]\n${displayText}` : trimmed,
        imageUrl: selectedImage ? imagePreview ?? undefined : undefined,
        created_at: new Date().toISOString(),
      };

      appendMessage(userMessage);
      setMessage("");
      const response = await mutateAsync({
        message: displayText,
        conversationId: currentConversation?.id === "draft" ? undefined : currentConversation?.id,
        image: selectedImage ?? undefined,
      });
      if (selectedImage === imageFile) {
        setImageFile(null);
        setImagePreview(null);
      }
      return handleChatResponse(response);
    },
    [appendMessage, currentConversation?.id, handleChatResponse, imageFile, isPending, mutateAsync],
  );

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void sendMessage(message);
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if ((message.trim() || imageFile) && !isPending) void sendMessage(message);
    }
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Please choose a JPG, PNG, or WEBP image.");
      event.target.value = "";
      return;
    }
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const removeImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(null);
    setImagePreview(null);
    if (imageInputRef.current) imageInputRef.current.value = "";
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
    removeImage();
  };

  return (
    <main className="flex h-[calc(100vh-3.5rem)] min-h-0 flex-col bg-cream">
      <header className="border-b border-cream-200 bg-white px-4 py-2.5 sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold text-[#263238] sm:text-base">{title}</h1>
          </div>
          <button
            type="button"
            onClick={handleNewChat}
            className="btn-primary h-9 shrink-0 px-3"
            aria-label="Start a new chat"
          >
            <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">New chat</span>
          </button>
        </div>
      </header>

      <section className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:py-8">
        <ChatMessages messages={messages} isResponding={mutation.isPending} />
      </section>

      <form onSubmit={handleSubmit} className="border-t border-cream-200 bg-white/95 px-3 py-2.5 sm:px-4">
        <div className="mx-auto max-w-4xl">
          <div className="rounded-lg border border-cream-200 bg-white px-3 py-2 shadow-sm focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100">
            <label className="sr-only" htmlFor="chat-message">
              Message
            </label>
            {isMobileVoiceCapture ? (
              <div className="mb-2 flex min-h-11 items-center gap-3 rounded-lg bg-brand-50 px-3 py-2 text-brand-700 sm:hidden">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100">
                  <Mic className="h-4 w-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold">Recording</p>
                  <p className="truncate text-xs font-medium text-brand-700">Tap the mic button to stop</p>
                </div>
                <VoiceStatus status={voice.status} audioLevel={voice.audioLevel} compact />
              </div>
            ) : null}

            {imagePreview ? (
              <div className="relative mb-2 w-fit rounded-lg border border-cream-200 bg-cream p-1">
                <img src={imagePreview} alt="Selected agriculture image" className="h-24 w-24 rounded-md object-cover" />
                <button type="button" onClick={removeImage} className="absolute -right-2 -top-2 rounded-full bg-[#263238] p-1 text-white shadow-sm" aria-label="Remove selected image" title="Remove selected image">
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            ) : null}

            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <textarea
                id="chat-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                rows={1}
                className={`max-h-28 min-h-10 flex-1 resize-none border-0 bg-transparent px-0 py-2 text-sm leading-6 text-[#263238] outline-none placeholder:text-[#607D8B] sm:min-h-9 ${
                  isMobileVoiceCapture ? "hidden sm:block" : ""
                }`}
                placeholder="သီးနှံ၊ အပင်ရောဂါ၊ မြေဩဇာအကြောင်း မေးပါ..."
              />
              <div className="flex shrink-0 items-center justify-between gap-2 sm:justify-end">
                <input ref={imageInputRef} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" className="sr-only" onChange={handleImageChange} />
                <button type="button" onClick={() => imageInputRef.current?.click()} disabled={mutation.isPending} className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-cream-200 bg-white text-[#263238] transition hover:bg-brand-50 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-50" aria-label="Attach agriculture image" title="Attach agriculture image">
                  <ImagePlus className="h-5 w-5" aria-hidden="true" />
                </button>
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
                          ? "border-brand-600 bg-brand-50 text-brand-700 focus:ring-brand-100"
                          : "border-cream-200 bg-white text-[#263238] hover:bg-brand-50 focus:ring-brand-100"
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
                    disabled={mutation.isPending}
                    onToggleVoiceMode={voice.toggleVoiceMode}
                    onToggleMute={voice.toggleMute}
                    onReplay={voice.replayLastResponse}
                    onStopSpeaking={voice.stopSpeaking}
                    onExit={voice.stopVoiceMode}
                  />
                  <button
                    type="submit"
                    className="btn-primary h-10 w-10 shrink-0 p-0"
                    disabled={
                      (!message.trim() && !imageFile) ||
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
          <p className="mt-1.5 hidden text-center text-[11px] text-[#607D8B] sm:block">Press Enter to send � Shift + Enter for a new line</p>
        </div>
      </form>
    </main>
  );
}



