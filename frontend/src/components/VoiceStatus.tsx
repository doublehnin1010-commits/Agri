import type { VoiceConversationStatus } from "../hooks/useVoiceConversation";

interface VoiceStatusProps {
  status: VoiceConversationStatus;
  audioLevel: number;
  compact?: boolean;
}

const STATUS_LABELS: Record<VoiceConversationStatus, string> = {
  idle: "Idle",
  listening: "Listening",
  recording: "Recording",
  uploading: "Uploading",
  transcribing: "Transcribing",
  thinking: "Thinking",
  speaking: "Speaking",
  completed: "Completed",
};

export function VoiceStatus({ status, audioLevel, compact = false }: VoiceStatusProps) {
  const level = Math.min(1, Math.max(0, audioLevel * 12));
  const bars = [0.35, 0.6, 0.9, 0.55, 0.4];

  return (
    <div
      className={`flex min-h-6 items-center gap-2 text-xs font-semibold ${
        compact ? "text-brand-700" : "text-[#607D8B]"
      }`}
      aria-live="polite"
    >
      {compact ? <span className="sr-only">{STATUS_LABELS[status]}</span> : <span>{STATUS_LABELS[status]}</span>}
      {status === "recording" ? (
        <span className="flex h-5 items-center gap-0.5" aria-hidden="true">
          {bars.map((bar, index) => (
            <span
              key={index}
              className="w-1 rounded-full bg-brand-600 transition-all"
              style={{ height: `${8 + 16 * Math.max(level, bar * 0.35)}px` }}
            />
          ))}
        </span>
      ) : null}
    </div>
  );
}
