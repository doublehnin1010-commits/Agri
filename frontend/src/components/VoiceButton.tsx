import { Mic, MicOff, RotateCcw, Volume2, VolumeX, X } from "lucide-react";
import type { VoiceConversationStatus } from "../hooks/useVoiceConversation";

interface VoiceButtonProps {
  isVoiceMode: boolean;
  status: VoiceConversationStatus;
  isMuted: boolean;
  canReplay: boolean;
  disabled?: boolean;
  onToggleVoiceMode: () => void;
  onToggleMute: () => void;
  onReplay: () => void;
  onStopSpeaking: () => void;
  onExit: () => void;
}

export function VoiceButton({
  isVoiceMode,
  status,
  isMuted,
  canReplay,
  disabled = false,
  onToggleVoiceMode,
  onToggleMute,
  onReplay,
  onStopSpeaking,
  onExit,
}: VoiceButtonProps) {
  const isSpeaking = status === "speaking";

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
      <button
        type="button"
        onClick={onToggleVoiceMode}
        disabled={disabled && !isVoiceMode}
        className={`relative inline-flex h-10 w-10 items-center justify-center rounded-lg border transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50 ${
          isVoiceMode
            ? "border-brand-600 bg-brand-50 text-brand-700 focus:ring-brand-100"
            : "border-cream-200 bg-white text-[#263238] hover:bg-brand-50 focus:ring-brand-100"
        }`}
        aria-label={isVoiceMode ? "Exit voice mode" : "Start voice mode"}
        aria-pressed={isVoiceMode}
        title={isVoiceMode ? "Exit voice mode" : "Start voice mode"}
      >
        {isVoiceMode ? (
          <>
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-brand-600 ring-2 ring-white" />
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
            className="hidden h-10 w-10 items-center justify-center rounded-lg border border-cream-200 bg-white text-[#263238] transition hover:bg-brand-50 focus:outline-none focus:ring-4 focus:ring-brand-100 sm:inline-flex"
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
            className="hidden h-10 w-10 items-center justify-center rounded-lg border border-cream-200 bg-white text-[#263238] transition hover:bg-brand-50 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-50 sm:inline-flex"
            aria-label={isSpeaking ? "Stop speaking" : "Replay last response"}
            title={isSpeaking ? "Stop speaking" : "Replay last response"}
          >
            {isSpeaking ? <X className="h-5 w-5" /> : <RotateCcw className="h-5 w-5" />}
          </button>
          <button
            type="button"
            onClick={onExit}
            className="hidden h-10 w-10 items-center justify-center rounded-lg border border-cream-200 bg-white text-[#263238] transition hover:bg-brand-50 focus:outline-none focus:ring-4 focus:ring-brand-100 sm:inline-flex"
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

