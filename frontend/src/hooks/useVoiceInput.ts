import { useSpeechRecognition } from "./useSpeechRecognition";
import { useAudioRecording } from "./useAudioRecording";
import type { SpeechRecognitionLanguage, SpeechRecognitionStatus, VoiceInputMode } from "../types/speech";
import { getVoiceInputMode, isVoiceInputSupported } from "../utils/voiceCapability";

interface UseVoiceInputOptions {
  language: SpeechRecognitionLanguage;
  onTranscript: (text: string) => void;
  onInterimTranscript?: (text: string) => void;
  onListeningChange?: (isListening: boolean) => void;
}

interface UseVoiceInputResult {
  mode: VoiceInputMode;
  isSupported: boolean;
  status: SpeechRecognitionStatus;
  isListening: boolean;
  language: SpeechRecognitionLanguage;
  setLanguage: (language: SpeechRecognitionLanguage) => void;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
}

const idleVoiceInput: UseVoiceInputResult = {
  mode: "unavailable",
  isSupported: false,
  status: "idle",
  isListening: false,
  language: "my-MM",
  setLanguage: () => undefined,
  startListening: () => undefined,
  stopListening: () => undefined,
  toggleListening: () => undefined,
};

export function useVoiceInput(options: UseVoiceInputOptions): UseVoiceInputResult {
  const mode = getVoiceInputMode();
  const isSupported = isVoiceInputSupported();

  const speech = useSpeechRecognition(options);

  const audio = useAudioRecording({
    language: options.language,
    onTranscript: options.onTranscript,
    onListeningChange: options.onListeningChange,
  });

  if (!isSupported) {
    return { ...idleVoiceInput, mode, language: options.language };
  }

  if (mode === "speech-api") {
    return {
      mode,
      isSupported: true,
      status: speech.status,
      isListening: speech.isListening,
      language: speech.language,
      setLanguage: speech.setLanguage,
      startListening: speech.startListening,
      stopListening: speech.stopListening,
      toggleListening: speech.toggleListening,
    };
  }

  return {
    mode,
    isSupported: true,
    status: audio.status,
    isListening: audio.isListening,
    language: audio.language,
    setLanguage: audio.setLanguage,
    startListening: () => {
      void audio.startListening();
    },
    stopListening: audio.stopListening,
    toggleListening: audio.toggleListening,
  };
}
