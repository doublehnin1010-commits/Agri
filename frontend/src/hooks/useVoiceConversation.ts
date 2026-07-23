import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { speechToText, textToSpeech } from "../services/voiceService";
import { useRecorder } from "./useRecorder";
import type { SpeechRecognitionLanguage } from "../types/speech";

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
  language: SpeechRecognitionLanguage;
  setLanguage: (language: SpeechRecognitionLanguage) => void;
  toggleVoiceMode: () => void;
  stopVoiceMode: () => void;
  toggleMute: () => void;
  stopSpeaking: () => void;
  replayLastResponse: () => void;
  speakResponse: (text: string) => void;
}

export function useVoiceConversation({
  disabled = false,
  onTranscript,
}: UseVoiceConversationOptions): UseVoiceConversationResult {
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [status, setStatus] = useState<VoiceConversationStatus>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [lastSpokenText, setLastSpokenText] = useState("");
  const [language, setLanguageState] = useState<SpeechRecognitionLanguage>("my-MM");
  const isVoiceModeRef = useRef(false);
  const disabledRef = useRef(disabled);
  const mutedRef = useRef(isMuted);
  const onTranscriptRef = useRef(onTranscript);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const languageRef = useRef<SpeechRecognitionLanguage>("my-MM");

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

  const clearAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  const speak = useCallback(async (
    text: string,
    options: { requireVoiceMode?: boolean; resumeListening?: boolean } = {},
  ) => {
    const requireVoiceMode = options.requireVoiceMode ?? true;
    const resumeListening = options.resumeListening ?? true;
    setLastSpokenText(text);
    if (mutedRef.current) {
      if (resumeListening) startListening();
      else setStatus("completed");
      return;
    }

    clearAudio();
    setStatus("speaking");
    try {
      const blob = await textToSpeech(text, languageRef.current);
      if ((requireVoiceMode && !isVoiceModeRef.current) || mutedRef.current) return;
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioUrlRef.current = url;
      audioRef.current = audio;
      audio.onended = () => {
        clearAudio();
        setStatus("completed");
        if (resumeListening) startListening();
      };
      audio.onerror = () => {
        clearAudio();
        toast.error("Could not play the generated speech.");
        if (resumeListening) startListening();
        else setStatus("completed");
      };
      await audio.play();
    } catch (error) {
      clearAudio();
      toast.error(getApiErrorMessage(error));
      if (resumeListening) startListening();
      else setStatus("completed");
    }
  }, [clearAudio, startListening]);

  const handleRecordingReady = useCallback(
    async (audio: Blob, filename: string) => {
      if (!isVoiceModeRef.current) return;
      setStatus("uploading");

      try {
        const transcript = await speechToText(
          audio,
          filename,
          (event) => {
            if (event.total && event.loaded >= event.total) {
              setStatus("transcribing");
            }
          },
          languageRef.current,
        );
        setStatus("thinking");
        const text = transcript.text.trim();
        if (!text) {
          startListening();
          return;
        }

        const answerText = await onTranscriptRef.current(text);
        if (!isVoiceModeRef.current) return;

        if (answerText?.trim()) {
          void speak(answerText);
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
    clearAudio();
    if (isVoiceModeRef.current) startListening();
    else setStatus("idle");
  }, [clearAudio, startListening]);

  const stopVoiceMode = useCallback(() => {
    isVoiceModeRef.current = false;
    setIsVoiceMode(false);
    setStatus("idle");
    cancelRecording();
    clearAudio();
  }, [cancelRecording, clearAudio]);

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
      if (next) clearAudio();
      return next;
    });
  }, [clearAudio]);

  const replayLastResponse = useCallback(() => {
    if (!lastSpokenText.trim()) return;
    void speak(lastSpokenText, {
      requireVoiceMode: false,
      resumeListening: isVoiceModeRef.current,
    });
  }, [lastSpokenText, speak]);

  const speakResponse = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    void speak(trimmed, {
      requireVoiceMode: false,
      resumeListening: false,
    });
  }, [speak]);

  const setLanguage = useCallback((nextLanguage: SpeechRecognitionLanguage) => {
    languageRef.current = nextLanguage;
    setLanguageState(nextLanguage);
  }, []);

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
    language,
    setLanguage,
    toggleVoiceMode,
    stopVoiceMode,
    toggleMute,
    stopSpeaking,
    replayLastResponse,
    speakResponse,
  };
}
