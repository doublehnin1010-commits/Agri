export type VoiceInputMode = "speech-api" | "media-recorder" | "unavailable";

export type SpeechRecognitionLanguage = "my-MM" | "en-US";

export type SpeechRecognitionStatus = "idle" | "listening" | "processing";

export type SpeechRecognitionErrorCode =
  | "not-allowed"
  | "no-speech"
  | "aborted"
  | "audio-capture"
  | "network"
  | "service-not-allowed"
  | "bad-grammar"
  | "language-not-supported"
  | "timeout"
  | "unsupported";

export interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

export interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

export interface SpeechRecognitionResultList {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

export interface SpeechRecognitionErrorEvent extends Event {
  readonly error: SpeechRecognitionErrorCode;
  readonly message: string;
}

export interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

export interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: ((this: BrowserSpeechRecognition, event: Event) => void) | null;
  onend: ((this: BrowserSpeechRecognition, event: Event) => void) | null;
  onerror: ((this: BrowserSpeechRecognition, event: SpeechRecognitionErrorEvent) => void) | null;
  onresult: ((this: BrowserSpeechRecognition, event: SpeechRecognitionEvent) => void) | null;
  onnomatch: ((this: BrowserSpeechRecognition, event: SpeechRecognitionEvent) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

export type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

export interface SpeechLanguageOption {
  code: SpeechRecognitionLanguage;
  label: string;
  shortLabel: string;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}
