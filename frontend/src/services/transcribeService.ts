import { apiClient } from "../api/client";
import type { SpeechRecognitionLanguage } from "../types/speech";

export interface TranscribeResponse {
  transcript: string;
}

export async function transcribeAudio(
  audio: Blob,
  language: SpeechRecognitionLanguage,
  filename = "recording.webm",
): Promise<string> {
  const formData = new FormData();
  formData.append("file", audio, filename);
  formData.append("language", language);

  const { data } = await apiClient.post<TranscribeResponse>("/transcribe", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return data.transcript;
}
