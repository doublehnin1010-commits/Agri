import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, RefreshCw, Trash2, UploadCloud } from "lucide-react";
import { ChangeEvent, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../../api/client";
import { deleteDocument, listDocuments, processDocument, uploadDocument, type AgricultureDocument } from "../../services/documentService";
import { formatDate } from "../../utils/answer";

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const { data = [], isLoading } = useQuery({ queryKey: ["documents"], queryFn: listDocuments, refetchInterval: 4000 });

  const stats = useMemo(() => ({
    documents: data.length,
    chunks: data.reduce((sum, item) => sum + item.chunk_count, 0),
    processing: data.filter((item) => item.status === "pending" || item.status === "processing").length,
  }), [data]);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a PDF, DOCX, or TXT document first.");
      return uploadDocument(file, setProgress);
    },
    onSuccess: () => {
      toast.success("Document uploaded");
      setFile(null);
      setProgress(0);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      toast.success("Document deleted");
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const processMutation = useMutation({
    mutationFn: processDocument,
    onSuccess: () => {
      toast.success("Re-processing started");
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
    setProgress(0);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#263238]">Agriculture Documents</h1>
        <p className="mt-2 text-sm text-[#607D8B]">Upload PDF, DOCX, or TXT farming references for the RAG knowledge base.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Documents" value={stats.documents} />
        <Stat label="Chunks" value={stats.chunks} />
        <Stat label="Processing" value={stats.processing} />
      </div>

      <section className="rounded-lg border border-cream-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="flex min-h-24 flex-1 cursor-pointer items-center justify-center rounded-lg border border-dashed border-cream-200 bg-cream px-4 text-center text-sm font-medium text-[#607D8B] hover:border-brand-400 hover:bg-brand-50">
            <input type="file" accept=".pdf,.docx,.txt" className="sr-only" onChange={handleFileChange} />
            <span>{file ? file.name : "Choose agriculture PDF, DOCX, or TXT"}</span>
          </label>
          <button type="button" className="btn-primary h-11" onClick={() => uploadMutation.mutate()} disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
            Upload
          </button>
        </div>
        {uploadMutation.isPending ? <div className="mt-3 h-2 rounded-full bg-brand-50"><div className="h-2 rounded-full bg-brand-600" style={{ width: `${progress}%` }} /></div> : null}
      </section>

      <section className="overflow-hidden rounded-lg border border-cream-200 bg-white shadow-sm">
        <div className="border-b border-cream-200 px-4 py-3 text-sm font-semibold text-[#263238]">Knowledge Base</div>
        {isLoading ? <div className="p-6 text-sm text-[#607D8B]">Loading documents...</div> : null}
        {!isLoading && !data.length ? <div className="p-8 text-center text-sm text-[#607D8B]">No agriculture documents uploaded yet.</div> : null}
        {data.length ? <div className="divide-y divide-cream-200">{data.map((doc) => <DocumentRow key={doc.id} doc={doc} onDelete={() => deleteMutation.mutate(doc.id)} onProcess={() => processMutation.mutate(doc.id)} busy={deleteMutation.isPending || processMutation.isPending} />)}</div> : null}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border border-cream-200 bg-white p-4"><p className="text-xs font-semibold uppercase text-[#607D8B]">{label}</p><p className="mt-2 text-2xl font-bold text-[#263238]">{value.toLocaleString()}</p></div>;
}

function DocumentRow({ doc, onDelete, onProcess, busy }: { doc: AgricultureDocument; onDelete: () => void; onProcess: () => void; busy: boolean }) {
  const statusClass = doc.status === "completed" ? "bg-brand-50 text-brand-700" : doc.status === "failed" ? "bg-brand-100 text-brand-700" : "bg-brand-50 text-brand-700";
  return (
    <div className="grid gap-3 p-4 md:grid-cols-[1fr_auto] md:items-center">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-brand-600" />
          <p className="truncate font-semibold text-[#263238]">{doc.filename}</p>
          <span className={`rounded-full px-2 py-1 text-xs font-bold ${statusClass}`}>{doc.status}</span>
        </div>
        <p className="mt-2 text-sm text-[#607D8B]">{doc.file_type.toUpperCase()} · {(doc.file_size / 1024 / 1024).toFixed(2)} MB · {doc.chunk_count} chunks · uploaded {formatDate(doc.uploaded_at)}</p>
        {doc.error ? <p className="mt-2 text-sm text-brand-700">{doc.error}</p> : null}
      </div>
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border border-cream-200 p-2 text-[#607D8B] hover:bg-brand-50" onClick={onProcess} disabled={busy} aria-label="Re-process document" title="Re-process document"><RefreshCw className="h-4 w-4" /></button>
        <button type="button" className="rounded-lg border border-brand-100 p-2 text-brand-700 hover:bg-brand-50" onClick={onDelete} disabled={busy} aria-label="Delete document" title="Delete document"><Trash2 className="h-4 w-4" /></button>
      </div>
    </div>
  );
}

