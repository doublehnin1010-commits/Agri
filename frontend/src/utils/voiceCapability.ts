import type { VoiceInputMode } from "../types/speech";
import { getSpeechRecognitionConstructor } from "./speechRecognition";

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
  if (getSpeechRecognitionConstructor()) return "speech-api";
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
  const mode = getVoiceInputMode();
  if (mode === "media-recorder" && !isSecureMicContext()) {
    return "Voice needs HTTPS. Open the https:// link from Vite and accept the certificate on your phone.";
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
  ];

  for (const candidate of candidates) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }

  return "";
}
