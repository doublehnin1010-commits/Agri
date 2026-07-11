import type { VoiceConversationStatus } from "../hooks/useVoiceConversation";

interface VoiceStatusProps {
  status: VoiceConversationStatus;
  audioLevel: number;
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

export function VoiceStatus({ status, audioLevel }: VoiceStatusProps) {
  const level = Math.min(1, Math.max(0, audioLevel * 12));
  const bars = [0.35, 0.6, 0.9, 0.55, 0.4];

  return (
    <div className="flex min-h-6 items-center gap-2 text-xs font-semibold text-slate-500" aria-live="polite">
      <span>{STATUS_LABELS[status]}</span>
      {status === "recording" ? (
        <span className="flex h-5 items-center gap-0.5" aria-hidden="true">
          {bars.map((bar, index) => (
            <span
              key={index}
              className="w-1 rounded-full bg-red-500 transition-all"
              style={{ height: `${8 + 16 * Math.max(level, bar * 0.35)}px` }}
            />
          ))}
        </span>
      ) : null}
    </div>
  );
}
