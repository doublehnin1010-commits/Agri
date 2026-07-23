import { apiClient } from "../api/client";
import type { QuizStartPayload, QuizStartResponse, QuizSubmitPayload, QuizSubmitResponse } from "../types";

export async function startQuiz(payload: QuizStartPayload): Promise<QuizStartResponse> {
  const { data } = await apiClient.post<QuizStartResponse>("/quiz/start", payload);
  return data;
}

export async function submitQuiz(payload: QuizSubmitPayload): Promise<QuizSubmitResponse> {
  const { data } = await apiClient.post<QuizSubmitResponse>("/quiz/submit", payload);
  return data;
}
