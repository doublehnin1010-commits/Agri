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

  // Let the browser add the multipart boundary. Setting Content-Type manually
  // breaks uploads in some browser/axios combinations.
  const { data } = await apiClient.post<TranscribeResponse>("/transcribe", formData);

  return data.transcript;
}
