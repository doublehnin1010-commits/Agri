import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../api/client";
import { transcribeAudio } from "../services/transcribeService";
import type { SpeechRecognitionLanguage, SpeechRecognitionStatus } from "../types/speech";
import { getPreferredAudioMimeType } from "../utils/voiceCapability";

interface UseAudioRecordingOptions {
  language: SpeechRecognitionLanguage;
  onTranscript: (text: string) => void;
  onListeningChange?: (isListening: boolean) => void;
}

interface UseAudioRecordingResult {
  status: SpeechRecognitionStatus;
  isListening: boolean;
  language: SpeechRecognitionLanguage;
  setLanguage: (language: SpeechRecognitionLanguage) => void;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
}

export function useAudioRecording({
  language,
  onTranscript,
  onListeningChange,
}: UseAudioRecordingOptions): UseAudioRecordingResult {
  const [status, setStatus] = useState<SpeechRecognitionStatus>("idle");
  const [activeLanguage, setActiveLanguage] = useState<SpeechRecognitionLanguage>(language);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeTypeRef = useRef("");
  const onTranscriptRef = useRef(onTranscript);
  const onListeningChangeRef = useRef(onListeningChange);

  const isListening = status === "listening";

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onListeningChangeRef.current = onListeningChange;
  }, [onListeningChange]);

  useEffect(() => {
    setActiveLanguage(language);
  }, [language]);

  const setListeningState = useCallback((listening: boolean) => {
    setStatus(listening ? "listening" : "idle");
    onListeningChangeRef.current?.(listening);
  }, []);

  const cleanupStream = useCallback(() => {
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    if (mediaStreamRef.current) {
      for (const track of mediaStreamRef.current.getTracks()) {
        track.stop();
      }
      mediaStreamRef.current = null;
    }
  }, []);

  const processRecording = useCallback(
    async (blob: Blob) => {
      if (!blob.size) {
        toast.error("No speech was detected. Please try speaking again.");
        return;
      }

      setStatus("processing");
      try {
        const extension = mimeTypeRef.current.includes("mp4")
          ? "recording.mp4"
          : mimeTypeRef.current.includes("ogg")
            ? "recording.ogg"
            : "recording.webm";
        const transcript = await transcribeAudio(blob, activeLanguage, extension);
        onTranscriptRef.current(transcript);
      } catch (error) {
        toast.error(getApiErrorMessage(error));
      } finally {
        setStatus("idle");
      }
    },
    [activeLanguage],
  );

  const startListening = useCallback(async () => {
    if (status === "listening" || status === "processing") return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getPreferredAudioMimeType();
      mimeTypeRef.current = mimeType;

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      chunksRef.current = [];
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mimeTypeRef.current || recorder.mimeType || "audio/webm",
        });
        cleanupStream();
        setListeningState(false);
        void processRecording(blob);
      };

      recorder.onerror = () => {
        cleanupStream();
        setListeningState(false);
        toast.error("Recording failed. Please try again.");
      };

      recorder.start();
      setListeningState(true);
    } catch (error) {
      cleanupStream();
      setListeningState(false);

      if (error instanceof DOMException && error.name === "NotAllowedError") {
        toast.error("Microphone access was denied. Please allow microphone permission and try again.");
        return;
      }

      toast.error("Could not access the microphone. Please try again.");
    }
  }, [cleanupStream, processRecording, setListeningState, status]);

  const stopListening = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
  }, []);

  const toggleListening = useCallback(() => {
    if (status === "listening") {
      stopListening();
      return;
    }
    void startListening();
  }, [startListening, status, stopListening]);

  const setLanguage = useCallback(
    (nextLanguage: SpeechRecognitionLanguage) => {
      if (status === "listening" || status === "processing") return;
      setActiveLanguage(nextLanguage);
    },
    [status],
  );

  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
      }
      cleanupStream();
    };
  }, [cleanupStream]);

  return {
    status,
    isListening,
    language: activeLanguage,
    setLanguage,
    startListening,
    stopListening,
    toggleListening,
  };
}
