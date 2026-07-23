import { apiClient } from "../api/client";
import type { AxiosProgressEvent } from "axios";

export interface SpeechToTextResponse {
  success: boolean;
  text: string;
  language: string;
}

export async function textToSpeech(text: string, language = "my-MM"): Promise<Blob> {
  const { data } = await apiClient.post<Blob>(
    "/text-to-speech",
    { text, language },
    { responseType: "blob", timeout: 120_000 },
  );
  return data;
}

export async function speechToText(
  audio: Blob,
  filename = "recording.webm",
  onUploadProgress?: (event: AxiosProgressEvent) => void,
  language = "my-MM",
): Promise<SpeechToTextResponse> {
  const formData = new FormData();
  formData.append("audio", audio, filename);
  formData.append("language", language);

  const { data } = await apiClient.post<SpeechToTextResponse>("/speech-to-text", formData, {
    onUploadProgress,
    timeout: 120_000,
  });

  return data;
}
