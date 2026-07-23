import { apiClient } from "../api/client";
import type { FavoriteProverb, FavoriteStatus } from "../types";

export async function addFavorite(proverbId: string): Promise<FavoriteStatus> {
  const { data } = await apiClient.post<FavoriteStatus>(`/favorites/${proverbId}`);
  return data;
}

export async function removeFavorite(proverbId: string): Promise<FavoriteStatus> {
  const { data } = await apiClient.delete<FavoriteStatus>(`/favorites/${proverbId}`);
  return data;
}

export async function checkFavorite(proverbId: string): Promise<FavoriteStatus> {
  const { data } = await apiClient.get<FavoriteStatus>(`/favorites/check/${proverbId}`);
  return data;
}

export async function listFavorites(): Promise<FavoriteProverb[]> {
  const { data } = await apiClient.get<FavoriteProverb[]>("/favorites");
  return data;
}
