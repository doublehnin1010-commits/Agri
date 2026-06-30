import { apiClient } from "../api/client";
import type { Proverb } from "../types";

export type ProverbPayload = Pick<Proverb, "proverb" | "meaning"> & {
  keyword?: string;
  example?: string;
};

function normalizeProverbs(data: unknown): Proverb[] {
  if (Array.isArray(data)) return data as Proverb[];
  if (data && typeof data === "object") {
    const record = data as { items?: Proverb[]; proverbs?: Proverb[]; results?: Proverb[] };
    return record.items ?? record.proverbs ?? record.results ?? [];
  }
  return [];
}

export async function listProverbs(): Promise<Proverb[]> {
  const { data } = await apiClient.get<unknown>("/proverbs");
  return normalizeProverbs(data);
}

export async function createProverb(payload: ProverbPayload): Promise<Proverb> {
  const { data } = await apiClient.post<Proverb>("/proverbs", {
    keyword: payload.keyword ?? "",
    proverb: payload.proverb,
    meaning: payload.meaning,
    example: payload.example ?? "",
  });
  return data;
}

export async function updateProverb(id: string, payload: ProverbPayload): Promise<Proverb> {
  const { data } = await apiClient.put<Proverb>(`/proverbs/${id}`, payload);
  return data;
}

export async function deleteProverb(id: string): Promise<{ success: boolean; deleted: number }> {
  const { data } = await apiClient.delete<{ success: boolean; deleted: number }>(`/proverbs/${id}`);
  return data;
}

export async function deleteAllProverbs(): Promise<{ success: boolean; deleted: number }> {
  const { data } = await apiClient.delete<{ success: boolean; deleted: number }>("/proverbs");
  return data;
}
