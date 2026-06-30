import type {
  SpeechLanguageOption,
  SpeechRecognitionConstructor,
  SpeechRecognitionErrorCode,
  SpeechRecognitionLanguage,
} from "../types/speech";

export const SPEECH_LANGUAGE_OPTIONS: SpeechLanguageOption[] = [
  { code: "my-MM", label: "Myanmar", shortLabel: "MM" },
  { code: "en-US", label: "English", shortLabel: "EN" },
];

export const UNSUPPORTED_BROWSER_MESSAGE =
  "Voice recognition is not supported on this browser.";

export function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function isSpeechRecognitionSupported(): boolean {
  return getSpeechRecognitionConstructor() !== null;
}

export function createSpeechRecognition(
  language: SpeechRecognitionLanguage,
): InstanceType<SpeechRecognitionConstructor> | null {
  const SpeechRecognitionClass = getSpeechRecognitionConstructor();
  if (!SpeechRecognitionClass) return null;

  const recognition = new SpeechRecognitionClass();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = language;
  recognition.maxAlternatives = 1;
  return recognition;
}

export function getSpeechErrorMessage(error: SpeechRecognitionErrorCode): string {
  switch (error) {
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone access was denied. Please allow microphone permission and try again.";
    case "no-speech":
      return "No speech was detected. Please try speaking again.";
    case "aborted":
      return "Voice recognition was cancelled.";
    case "audio-capture":
      return "No microphone was found. Please connect a microphone and try again.";
    case "network":
      return "A network error occurred during voice recognition. Please try again.";
    case "language-not-supported":
      return "The selected language is not supported for voice recognition.";
    case "timeout":
      return "Recognition timed out. Please try again.";
    case "unsupported":
      return UNSUPPORTED_BROWSER_MESSAGE;
    default:
      return "Voice recognition failed. Please try again.";
  }
}

export function getLanguageOption(
  language: SpeechRecognitionLanguage,
): SpeechLanguageOption {
  return (
    SPEECH_LANGUAGE_OPTIONS.find((option) => option.code === language) ??
    SPEECH_LANGUAGE_OPTIONS[0]
  );
}
