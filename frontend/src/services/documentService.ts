import { apiClient } from "../api/client";

export interface AgricultureDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  uploaded_at: string;
  processed_at?: string | null;
  chunk_count: number;
  error?: string | null;
}

export async function uploadDocument(file: File, onProgress?: (progress: number) => void) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<{ document_id: string; status: string; message: string }>("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      onProgress(Math.round((event.loaded * 100) / event.total));
    },
  });
  return data;
}

export async function listDocuments(): Promise<AgricultureDocument[]> {
  const { data } = await apiClient.get<{ documents: AgricultureDocument[] }>("/documents");
  return data.documents;
}

export async function deleteDocument(id: string) {
  const { data } = await apiClient.delete<{ success: boolean; deleted: number }>(`/documents/${id}`);
  return data;
}

export async function processDocument(id: string) {
  const { data } = await apiClient.post<{ success: boolean; status: string }>(`/documents/${id}/process`);
  return data;
}
