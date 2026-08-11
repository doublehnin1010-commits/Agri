import type { VoiceInputMode } from "../types/speech";

export function isMicrophoneAvailable(): boolean {
  return typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);
}

export function isSecureMicContext(): boolean {
  return typeof window !== "undefined" && window.isSecureContext;
}

export function isMediaRecorderSupported(): boolean {
  return typeof MediaRecorder !== "undefined";
}

export function getVoiceInputMode(): VoiceInputMode {
  if (typeof window === "undefined") return "unavailable";
  if (isMicrophoneAvailable() && isMediaRecorderSupported()) return "media-recorder";
  return "unavailable";
}

export function isVoiceInputSupported(): boolean {
  const mode = getVoiceInputMode();
  if (mode === "unavailable") return false;
  if (mode === "media-recorder" && !isSecureMicContext()) return false;
  return true;
}

export function getVoiceUnavailableMessage(): string {
  if (!isSecureMicContext()) {
    return "Voice needs HTTPS. Open the secure https:// version of this site and allow microphone access.";
  }
  return "Voice input is not supported on this browser.";
}

export function getPreferredAudioMimeType(): string {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/aac",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];

  for (const candidate of candidates) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }

  return "";
}
