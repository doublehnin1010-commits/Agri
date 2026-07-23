import { Mic, MicOff, RotateCcw, Volume2, VolumeX, X } from "lucide-react";
import type { VoiceConversationStatus } from "../hooks/useVoiceConversation";
import type { SpeechRecognitionLanguage } from "../types/speech";

interface VoiceButtonProps {
  isVoiceMode: boolean;
  status: VoiceConversationStatus;
  isMuted: boolean;
  canReplay: boolean;
  language: SpeechRecognitionLanguage;
  disabled?: boolean;
  onToggleVoiceMode: () => void;
  onToggleMute: () => void;
  onReplay: () => void;
  onStopSpeaking: () => void;
  onExit: () => void;
  onLanguageChange: (language: SpeechRecognitionLanguage) => void;
}

export function VoiceButton({
  isVoiceMode,
  status,
  isMuted,
  canReplay,
  language,
  disabled = false,
  onToggleVoiceMode,
  onToggleMute,
  onReplay,
  onStopSpeaking,
  onExit,
  onLanguageChange,
}: VoiceButtonProps) {
  const isSpeaking = status === "speaking";
  const isActiveMobile = isVoiceMode ? "hidden sm:inline-flex" : "inline-flex";

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
      <div
        className={`${isActiveMobile} h-10 items-center rounded-lg border border-slate-200 bg-slate-50 p-1`}
        role="group"
        aria-label="Voice input language"
      >
        {(["my-MM", "en-US"] as const).map((option) => {
          const selected = language === option;
          const label = option === "my-MM" ? "မြန်မာ" : "EN";
          return (
            <button
              key={option}
              type="button"
              onClick={() => onLanguageChange(option)}
              disabled={isVoiceMode}
              className={`h-8 rounded-md px-2 text-xs font-bold transition focus:outline-none focus:ring-2 focus:ring-brand-300 disabled:cursor-not-allowed ${
                selected
                  ? "bg-white text-brand-700 shadow-sm ring-1 ring-slate-200"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              aria-pressed={selected}
              title={isVoiceMode ? "Exit voice mode to change language" : `Use ${label} voice input`}
            >
              {label}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        onClick={onToggleVoiceMode}
        disabled={disabled && !isVoiceMode}
        className={`relative inline-flex h-10 w-10 items-center justify-center rounded-lg border transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50 ${
          isVoiceMode
            ? "border-red-300 bg-red-50 text-red-600 focus:ring-red-100"
            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 focus:ring-brand-100"
        }`}
        aria-label={isVoiceMode ? "Exit voice mode" : "Start voice mode"}
        aria-pressed={isVoiceMode}
        title={isVoiceMode ? "Exit voice mode" : "Start voice mode"}
      >
        {isVoiceMode ? (
          <>
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white" />
            <MicOff className="h-5 w-5" aria-hidden="true" />
          </>
        ) : (
          <Mic className="h-5 w-5" aria-hidden="true" />
        )}
      </button>

      {isVoiceMode ? (
        <>
          <button
            type="button"
            onClick={onToggleMute}
            className="hidden h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-100 sm:inline-flex"
            aria-label={isMuted ? "Unmute AI voice" : "Mute AI voice"}
            aria-pressed={isMuted}
            title={isMuted ? "Unmute AI voice" : "Mute AI voice"}
          >
            {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
          </button>
          <button
            type="button"
            onClick={isSpeaking ? onStopSpeaking : onReplay}
            disabled={!isSpeaking && !canReplay}
            className="hidden h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-100 disabled:cursor-not-allowed disabled:opacity-50 sm:inline-flex"
            aria-label={isSpeaking ? "Stop speaking" : "Replay last response"}
            title={isSpeaking ? "Stop speaking" : "Replay last response"}
          >
            {isSpeaking ? <X className="h-5 w-5" /> : <RotateCcw className="h-5 w-5" />}
          </button>
          <button
            type="button"
            onClick={onExit}
            className="hidden h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-100 sm:inline-flex"
            aria-label="Exit voice mode"
            title="Exit voice mode"
          >
            <X className="h-5 w-5" />
          </button>
        </>
      ) : null}
    </div>
  );
}
