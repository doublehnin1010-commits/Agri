import { Loader2, Mic, MicOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useVoiceInput } from "../hooks/useVoiceInput";
import type { SpeechRecognitionLanguage } from "../types/speech";
import { SPEECH_LANGUAGE_OPTIONS } from "../utils/speechRecognition";
import { getVoiceUnavailableMessage } from "../utils/voiceCapability";

interface VoiceButtonProps {
  onTranscript: (text: string) => void;
  onInterimTranscript?: (text: string) => void;
  disabled?: boolean;
  onListeningChange?: (isListening: boolean) => void;
}

export function VoiceButton({
  onTranscript,
  onInterimTranscript,
  disabled = false,
  onListeningChange,
}: VoiceButtonProps) {
  const [language, setLanguage] = useState<SpeechRecognitionLanguage>("my-MM");

  const {
    isSupported,
    isListening,
    status,
    toggleListening,
    setLanguage: setRecognitionLanguage,
  } = useVoiceInput({
    language,
    onTranscript,
    onInterimTranscript,
    onListeningChange,
  });

  useEffect(() => {
    setRecognitionLanguage(language);
  }, [language, setRecognitionLanguage]);

  const isBusy = disabled || status === "processing";
  const showListening = isListening;
  const unavailableMessage = getVoiceUnavailableMessage();

  if (!isSupported) {
    return (
      <button
        type="button"
        disabled
        className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-100 text-slate-400 sm:h-12 sm:w-12"
        aria-label="Voice input unavailable"
        title={unavailableMessage}
      >
        <MicOff className="h-5 w-5" aria-hidden="true" />
      </button>
    );
  }

  return (
    <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
      <div
        className="flex items-center gap-0.5 rounded-lg border border-slate-200 bg-slate-50 p-0.5"
        role="group"
        aria-label="Voice language"
      >
        {SPEECH_LANGUAGE_OPTIONS.map((option) => {
          const isActive = language === option.code;
          return (
            <button
              key={option.code}
              type="button"
              onClick={() => setLanguage(option.code)}
              disabled={showListening || isBusy}
              className={`rounded-md px-1.5 py-1 text-[10px] font-semibold transition sm:px-2 sm:text-xs ${
                isActive
                  ? "bg-white text-brand-700 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              } disabled:cursor-not-allowed disabled:opacity-50`}
              aria-pressed={isActive}
              aria-label={`Recognition language: ${option.label}`}
            >
              {option.shortLabel}
            </button>
          );
        })}
      </div>

      <div className="relative">
        {showListening && (
          <span
            className="absolute -right-0.5 -top-0.5 z-10 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white"
            aria-hidden="true"
          />
        )}
        {showListening && (
          <span
            className="absolute inset-0 animate-ping rounded-lg bg-red-400/30"
            aria-hidden="true"
          />
        )}
        <button
          type="button"
          onClick={toggleListening}
          disabled={isBusy}
          className={`relative inline-flex h-11 w-11 items-center justify-center rounded-lg border transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50 sm:h-12 sm:w-12 ${
            showListening
              ? "border-red-300 bg-red-50 text-red-600 focus:ring-red-100"
              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 focus:ring-brand-100"
          }`}
          aria-label={showListening ? "Stop voice input" : "Start voice input"}
          aria-pressed={showListening}
          title={showListening ? "Listening..." : "Voice input"}
        >
          {status === "processing" ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <Mic className={`h-5 w-5 ${showListening ? "animate-pulse" : ""}`} aria-hidden="true" />
          )}
        </button>
      </div>
    </div>
  );
}
