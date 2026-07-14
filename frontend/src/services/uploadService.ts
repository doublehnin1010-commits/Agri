import { apiClient } from "../api/client";
import type { ImportJobProgress, ImportJobUploadResponse } from "../types";

const POLL_INTERVAL_MS = 2000;
export type DatasetType = "docx" | "txt";

export async function importKnowledge(
  datasetType: DatasetType,
  proverbsFile: File,
  meaningsFile: File,
  englishMeaningsFile: File,
  onProgress?: (progress: ImportJobProgress) => void,
): Promise<ImportJobProgress> {
  const formData = new FormData();
  formData.append("dataset_type", datasetType);
  formData.append("proverbs_file", proverbsFile);
  formData.append("meanings_file", meaningsFile);
  formData.append("english_meanings_file", englishMeaningsFile);

  const { data } = await apiClient.post<ImportJobUploadResponse>("/import-docx", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  onProgress?.({
    job_id: data.job_id,
    status: "uploaded",
    step: "Uploading",
    current: 0,
    total: 0,
    progress: 0,
    failed: 0,
  });

  return pollImportJobStatus(data.job_id, onProgress);
}

export async function importDocx(
  proverbsFile: File,
  meaningsFile: File,
  englishMeaningsFile: File,
  onProgress?: (progress: ImportJobProgress) => void,
): Promise<ImportJobProgress> {
  return importKnowledge("docx", proverbsFile, meaningsFile, englishMeaningsFile, onProgress);
}

export async function getImportJobStatus(jobId: string): Promise<ImportJobProgress> {
  const { data } = await apiClient.get<ImportJobProgress>(`/import-docx/status/${jobId}`);
  return data;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function pollImportJobStatus(
  jobId: string,
  onProgress?: (progress: ImportJobProgress) => void,
): Promise<ImportJobProgress> {
  while (true) {
    const status = await getImportJobStatus(jobId);
    onProgress?.(status);

    if (status.status === "completed" || status.status === "failed") {
      return status;
    }

    await sleep(POLL_INTERVAL_MS);
  }
}
