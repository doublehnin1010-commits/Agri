import { apiClient } from "../api/client";
import type { ImageLibraryImportResult, ImageLibraryPayload, ImageLibraryRecord } from "../types";

export async function listImageLibraryRecords(): Promise<ImageLibraryRecord[]> {
  const { data } = await apiClient.get<ImageLibraryRecord[]>("/image-library");
  return data;
}

export async function importImageLibraryRecords(
  records: ImageLibraryPayload[],
): Promise<ImageLibraryImportResult> {
  const { data } = await apiClient.post<ImageLibraryImportResult>("/image-library/import", records);
  return data;
}
