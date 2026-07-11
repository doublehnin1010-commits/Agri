import { apiClient } from "../api/client";
import type { AxiosProgressEvent } from "axios";

export interface SpeechToTextResponse {
  success: boolean;
  text: string;
  language: string;
}

export async function speechToText(
  audio: Blob,
  filename = "recording.webm",
  onUploadProgress?: (event: AxiosProgressEvent) => void,
): Promise<SpeechToTextResponse> {
  const formData = new FormData();
  formData.append("audio", audio, filename);

  const { data } = await apiClient.post<SpeechToTextResponse>("/speech-to-text", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress,
    timeout: 120_000,
  });

  return data;
}
