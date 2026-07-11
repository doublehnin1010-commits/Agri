import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { speechToText } from "../services/voiceService";
import { useRecorder } from "./useRecorder";

export type VoiceConversationStatus =
  | "idle"
  | "listening"
  | "recording"
  | "uploading"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "completed";

interface UseVoiceConversationOptions {
  disabled?: boolean;
  onTranscript: (text: string) => Promise<string | undefined>;
}

interface UseVoiceConversationResult {
  isVoiceMode: boolean;
  status: VoiceConversationStatus;
  isMuted: boolean;
  audioLevel: number;
  lastSpokenText: string;
  toggleVoiceMode: () => void;
  stopVoiceMode: () => void;
  toggleMute: () => void;
  stopSpeaking: () => void;
  replayLastResponse: () => void;
}

function hasMyanmarText(text: string): boolean {
  return /[\u1000-\u109f]/.test(text);
}

function chooseVoice(text: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices?.() ?? [];
  const wantsMyanmar = hasMyanmarText(text);
  const myanmarVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("my"));
  if (wantsMyanmar && myanmarVoice) return myanmarVoice;
  return (
    myanmarVoice ??
    voices.find((voice) => voice.lang.toLowerCase().startsWith("en")) ??
    voices[0] ??
    null
  );
}

export function useVoiceConversation({
  disabled = false,
  onTranscript,
}: UseVoiceConversationOptions): UseVoiceConversationResult {
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [status, setStatus] = useState<VoiceConversationStatus>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [lastSpokenText, setLastSpokenText] = useState("");
  const isVoiceModeRef = useRef(false);
  const disabledRef = useRef(disabled);
  const mutedRef = useRef(isMuted);
  const onTranscriptRef = useRef(onTranscript);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    disabledRef.current = disabled;
  }, [disabled]);

  useEffect(() => {
    mutedRef.current = isMuted;
  }, [isMuted]);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const startListeningRef = useRef<() => void>(() => undefined);

  const startListening = useCallback(() => {
    if (!isVoiceModeRef.current || disabledRef.current) return;
    setStatus("listening");
    startListeningRef.current();
  }, []);

  const speak = useCallback((text: string) => {
    setLastSpokenText(text);
    if (mutedRef.current || !("speechSynthesis" in window)) {
      startListening();
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = chooseVoice(text);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = hasMyanmarText(text) ? "my-MM" : "en-US";
    }
    utterance.rate = hasMyanmarText(text) ? 0.9 : 1;

    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => {
      utteranceRef.current = null;
      setStatus("completed");
      startListening();
    };
    utterance.onerror = () => {
      utteranceRef.current = null;
      startListening();
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, [startListening]);

  const handleRecordingReady = useCallback(
    async (audio: Blob, filename: string) => {
      if (!isVoiceModeRef.current) return;
      setStatus("uploading");

      try {
        const transcript = await speechToText(audio, filename, (event) => {
          if (event.total && event.loaded >= event.total) {
            setStatus("transcribing");
          }
        });
        setStatus("thinking");
        const text = transcript.text.trim();
        if (!text) {
          startListening();
          return;
        }

        const answerText = await onTranscriptRef.current(text);
        if (!isVoiceModeRef.current) return;

        if (answerText?.trim()) {
          speak(answerText);
        } else {
          startListening();
        }
      } catch (error) {
        toast.error(getApiErrorMessage(error));
        startListening();
      }
    },
    [speak, startListening],
  );

  const {
    audioLevel,
    startRecording,
    cancelRecording,
  } = useRecorder({
    onRecordingReady: handleRecordingReady,
    onRecordingStart: () => setStatus("recording"),
    onError: (message) => {
      toast.error(message);
      setStatus("idle");
      setIsVoiceMode(false);
      isVoiceModeRef.current = false;
    },
  });

  useEffect(() => {
    startListeningRef.current = () => {
      void startRecording();
    };
  }, [startRecording]);

  const stopSpeaking = useCallback(() => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    utteranceRef.current = null;
    if (isVoiceModeRef.current) startListening();
    else setStatus("idle");
  }, [startListening]);

  const stopVoiceMode = useCallback(() => {
    isVoiceModeRef.current = false;
    setIsVoiceMode(false);
    setStatus("idle");
    cancelRecording();
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    utteranceRef.current = null;
  }, [cancelRecording]);

  const toggleVoiceMode = useCallback(() => {
    if (isVoiceModeRef.current) {
      stopVoiceMode();
      return;
    }
    isVoiceModeRef.current = true;
    setIsVoiceMode(true);
    startListening();
  }, [startListening, stopVoiceMode]);

  const toggleMute = useCallback(() => {
    setIsMuted((current) => {
      const next = !current;
      mutedRef.current = next;
      if (next && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      return next;
    });
  }, []);

  const replayLastResponse = useCallback(() => {
    if (!lastSpokenText.trim()) return;
    speak(lastSpokenText);
  }, [lastSpokenText, speak]);

  useEffect(() => {
    if (disabled && (status === "listening" || status === "recording")) {
      cancelRecording();
      setStatus("thinking");
    }
  }, [cancelRecording, disabled, status]);

  useEffect(() => stopVoiceMode, [stopVoiceMode]);

  return {
    isVoiceMode,
    status,
    isMuted,
    audioLevel,
    lastSpokenText,
    toggleVoiceMode,
    stopVoiceMode,
    toggleMute,
    stopSpeaking,
    replayLastResponse,
  };
}
