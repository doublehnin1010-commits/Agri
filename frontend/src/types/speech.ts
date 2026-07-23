export type VoiceInputMode = "media-recorder" | "unavailable";

export type SpeechRecognitionLanguage = "my-MM" | "en-US";

export type SpeechRecognitionStatus = "idle" | "listening" | "processing";

export interface SpeechLanguageOption {
  code: SpeechRecognitionLanguage;
  label: string;
  shortLabel: string;
}

