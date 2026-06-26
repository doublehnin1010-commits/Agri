import { apiClient } from "../api/client";
import type { ImportResult } from "../types";

export async function importDocx(
  proverbsFile: File,
  meaningsFile: File,
  onProgress?: (progress: number) => void,
): Promise<ImportResult> {
  const formData = new FormData();
  formData.append("proverbs_file", proverbsFile);
  formData.append("meanings_file", meaningsFile);

  const { data } = await apiClient.post<ImportResult>("/import-docx", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total) return;
      onProgress?.(Math.round((event.loaded * 100) / event.total));
    },
  });

  return data;
}
