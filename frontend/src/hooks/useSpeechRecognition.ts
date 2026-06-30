import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import type {
  BrowserSpeechRecognition,
  SpeechRecognitionErrorCode,
  SpeechRecognitionEvent,
  SpeechRecognitionLanguage,
  SpeechRecognitionStatus,
} from "../types/speech";
import {
  createSpeechRecognition,
  getSpeechErrorMessage,
  isSpeechRecognitionSupported,
} from "../utils/speechRecognition";

interface UseSpeechRecognitionOptions {
  language: SpeechRecognitionLanguage;
  onTranscript: (text: string) => void;
  onInterimTranscript?: (text: string) => void;
  onListeningChange?: (isListening: boolean) => void;
}

interface UseSpeechRecognitionResult {
  isSupported: boolean;
  status: SpeechRecognitionStatus;
  isListening: boolean;
  language: SpeechRecognitionLanguage;
  setLanguage: (language: SpeechRecognitionLanguage) => void;
  startListening: () => void;
  stopListening: () => void;
  toggleListening: () => void;
}

function collectFullTranscript(event: SpeechRecognitionEvent): string {
  let transcript = "";
  for (let index = 0; index < event.results.length; index += 1) {
    transcript += event.results[index]?.[0]?.transcript ?? "";
  }
  return transcript.trim();
}

export function useSpeechRecognition({
  language,
  onTranscript,
  onInterimTranscript,
  onListeningChange,
}: UseSpeechRecognitionOptions): UseSpeechRecognitionResult {
  const [status, setStatus] = useState<SpeechRecognitionStatus>("idle");
  const [activeLanguage, setActiveLanguage] = useState<SpeechRecognitionLanguage>(language);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const manualStopRef = useRef(false);
  const transcriptDeliveredRef = useRef(false);
  const transcriptRef = useRef("");
  const onTranscriptRef = useRef(onTranscript);
  const onInterimTranscriptRef = useRef(onInterimTranscript);
  const onListeningChangeRef = useRef(onListeningChange);

  const isSupported = isSpeechRecognitionSupported();
  const isListening = status === "listening";

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onInterimTranscriptRef.current = onInterimTranscript;
  }, [onInterimTranscript]);

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

  const cleanupRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition) {
      recognition.onstart = null;
      recognition.onend = null;
      recognition.onerror = null;
      recognition.onresult = null;
      recognition.abort();
    }
    recognitionRef.current = null;
    manualStopRef.current = false;
    transcriptDeliveredRef.current = false;
    transcriptRef.current = "";
    setListeningState(false);
    setStatus("idle");
  }, [setListeningState]);

  const deliverTranscript = useCallback((text: string) => {
    if (!text || transcriptDeliveredRef.current) return;
    transcriptDeliveredRef.current = true;
    setStatus("processing");
    onTranscriptRef.current(text);
    setStatus("idle");
  }, []);

  const finalizeListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition) {
      recognition.onstart = null;
      recognition.onend = null;
      recognition.onerror = null;
      recognition.onresult = null;
      recognition.abort();
    }

    const transcript = transcriptRef.current.trim();
    recognitionRef.current = null;
    setListeningState(false);

    if (transcript) {
      deliverTranscript(transcript);
      return;
    }

    toast.error(getSpeechErrorMessage("no-speech"));
  }, [deliverTranscript, setListeningState]);

  const restartRecognition = useCallback((recognition: BrowserSpeechRecognition) => {
    try {
      recognition.start();
    } catch {
      // Browser may reject an immediate restart; user can click the mic again.
    }
  }, []);

  const handleRecognitionEnd = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setListeningState(false);
      return;
    }

    const hasTranscript = transcriptRef.current.trim().length > 0;

    if (manualStopRef.current || hasTranscript) {
      finalizeListening();
      return;
    }

    restartRecognition(recognition);
  }, [finalizeListening, restartRecognition, setListeningState]);

  const handleRecognitionError = useCallback(
    (errorCode: SpeechRecognitionErrorCode) => {
      if (errorCode === "aborted") return;

      if (errorCode === "no-speech" && !manualStopRef.current) {
        return;
      }

      const recognition = recognitionRef.current;
      if (recognition) {
        recognition.onstart = null;
        recognition.onend = null;
        recognition.onerror = null;
        recognition.onresult = null;
        recognition.abort();
      }
      recognitionRef.current = null;
      setListeningState(false);
      toast.error(getSpeechErrorMessage(errorCode));
    },
    [setListeningState],
  );

  const startListening = useCallback(() => {
    if (!isSupported || status === "listening" || status === "processing") return;

    const recognition = createSpeechRecognition(activeLanguage);
    if (!recognition) {
      toast.error(getSpeechErrorMessage("unsupported"));
      return;
    }

    manualStopRef.current = false;
    transcriptDeliveredRef.current = false;
    transcriptRef.current = "";
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setListeningState(true);
    };

    recognition.onresult = (event) => {
      const fullTranscript = collectFullTranscript(event);
      if (!fullTranscript) return;

      transcriptRef.current = fullTranscript;
      onInterimTranscriptRef.current?.(fullTranscript);
    };

    recognition.onerror = (event) => {
      handleRecognitionError(event.error);
    };

    recognition.onend = () => {
      handleRecognitionEnd();
    };

    try {
      recognition.start();
    } catch {
      cleanupRecognition();
      toast.error("Voice recognition is already active. Please try again.");
    }
  }, [
    activeLanguage,
    cleanupRecognition,
    handleRecognitionEnd,
    handleRecognitionError,
    isSupported,
    setListeningState,
    status,
  ]);

  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;

    manualStopRef.current = true;
    recognition.stop();
  }, []);

  const toggleListening = useCallback(() => {
    if (status === "listening") {
      stopListening();
      return;
    }
    startListening();
  }, [startListening, status, stopListening]);

  const setLanguage = useCallback(
    (nextLanguage: SpeechRecognitionLanguage) => {
      if (status === "listening") return;
      setActiveLanguage(nextLanguage);
    },
    [status],
  );

  useEffect(() => {
    return () => {
      manualStopRef.current = true;
      const recognition = recognitionRef.current;
      if (recognition) {
        recognition.onstart = null;
        recognition.onend = null;
        recognition.onerror = null;
        recognition.onresult = null;
        recognition.abort();
      }
      recognitionRef.current = null;
    };
  }, []);

  return {
    isSupported,
    status,
    isListening,
    language: activeLanguage,
    setLanguage,
    startListening,
    stopListening,
    toggleListening,
  };
}
