import { useCallback, useEffect, useRef, useState } from "react";
import { getPreferredAudioMimeType } from "../utils/voiceCapability";

type RecorderStatus = "idle" | "recording";

interface UseRecorderOptions {
  onRecordingReady: (audio: Blob, filename: string) => void;
  onError?: (message: string) => void;
  onRecordingStart?: () => void;
  silenceMs?: number;
  maxRecordingMs?: number;
}

interface UseRecorderResult {
  status: RecorderStatus;
  isRecording: boolean;
  audioLevel: number;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  cancelRecording: () => void;
}

function getFilename(mimeType: string): string {
  if (mimeType.includes("mp4") || mimeType.includes("aac")) return "recording.m4a";
  if (mimeType.includes("mpeg") || mimeType.includes("mp3")) return "recording.mp3";
  if (mimeType.includes("wav")) return "recording.wav";
  return "recording.webm";
}

function getAudioLevel(data: Uint8Array): number {
  let total = 0;
  for (const value of data) {
    const normalized = (value - 128) / 128;
    total += normalized * normalized;
  }
  return Math.sqrt(total / data.length);
}

export function useRecorder({
  onRecordingReady,
  onError,
  onRecordingStart,
  silenceMs = 650,
  maxRecordingMs = 20_000,
}: UseRecorderOptions): UseRecorderResult {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [audioLevel, setAudioLevel] = useState(0);
  const chunksRef = useRef<Blob[]>([]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const startedAtRef = useRef(0);
  const lastVoiceAtRef = useRef(0);
  const heardVoiceRef = useRef(false);
  const cancelledRef = useRef(false);
  const mimeTypeRef = useRef("");
  const onRecordingReadyRef = useRef(onRecordingReady);
  const onErrorRef = useRef(onError);
  const onRecordingStartRef = useRef(onRecordingStart);

  useEffect(() => {
    onRecordingReadyRef.current = onRecordingReady;
  }, [onRecordingReady]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    onRecordingStartRef.current = onRecordingStart;
  }, [onRecordingStart]);

  const cleanup = useCallback(() => {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    audioContextRef.current?.close().catch(() => undefined);
    audioContextRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setAudioLevel(0);
  }, []);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
  }, []);

  const monitorSilence = useCallback((stream: MediaStream) => {
    const AudioContextClass = window.AudioContext;
    const audioContext = new AudioContextClass();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    audioContext.createMediaStreamSource(stream).connect(analyser);
    audioContextRef.current = audioContext;

    const data = new Uint8Array(analyser.fftSize);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      const level = getAudioLevel(data);
      const now = Date.now();
      setAudioLevel(level);

      if (level > 0.025) {
        heardVoiceRef.current = true;
        lastVoiceAtRef.current = now;
      }

      const hasMinimumAudio = now - startedAtRef.current > 450;
      const silenceElapsed = now - lastVoiceAtRef.current;
      if (heardVoiceRef.current && hasMinimumAudio && silenceElapsed >= silenceMs) {
        stopRecording();
        return;
      }

      animationRef.current = requestAnimationFrame(tick);
    };

    lastVoiceAtRef.current = Date.now();
    animationRef.current = requestAnimationFrame(tick);
  }, [silenceMs, stopRecording]);

  const startRecording = useCallback(async () => {
    if (status === "recording") return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onErrorRef.current?.("Voice recording is not supported on this browser.");
      return;
    }

    try {
      cancelledRef.current = false;
      heardVoiceRef.current = false;
      chunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      const mimeType = getPreferredAudioMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

      streamRef.current = stream;
      recorderRef.current = recorder;
      mimeTypeRef.current = mimeType || recorder.mimeType || "audio/webm";
      startedAtRef.current = Date.now();

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onerror = () => {
        cleanup();
        setStatus("idle");
        onErrorRef.current?.("Recording failed. Please try again.");
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current });
        const filename = getFilename(mimeTypeRef.current);
        const wasCancelled = cancelledRef.current;
        const heardVoice = heardVoiceRef.current;
        cleanup();
        setStatus("idle");
        if (!wasCancelled && !heardVoice) {
          onErrorRef.current?.("No speech was detected. Please try speaking again.");
          return;
        }
        if (!wasCancelled && blob.size > 0) {
          onRecordingReadyRef.current(blob, filename);
        }
      };

      recorder.start(250);
      setStatus("recording");
      onRecordingStartRef.current?.();
      monitorSilence(stream);
      timeoutRef.current = window.setTimeout(stopRecording, maxRecordingMs);
    } catch (error) {
      cleanup();
      setStatus("idle");
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        onErrorRef.current?.("Microphone access was denied. Please allow microphone permission and try again.");
        return;
      }
      onErrorRef.current?.("Could not access the microphone. Please try again.");
    }
  }, [cleanup, maxRecordingMs, monitorSilence, status, stopRecording]);

  const cancelRecording = useCallback(() => {
    cancelledRef.current = true;
    stopRecording();
    cleanup();
    setStatus("idle");
  }, [cleanup, stopRecording]);

  useEffect(() => cleanup, [cleanup]);

  return {
    status,
    isRecording: status === "recording",
    audioLevel,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
