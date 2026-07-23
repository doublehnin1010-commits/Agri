import { CheckCircle2, FileText, Loader2, UploadCloud, X } from "lucide-react";
import { DragEvent, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../../api/client";
import { importKnowledge, type DatasetType } from "../../services/uploadService";
import type { ImportJobProgress } from "../../types";

type FileKind = "proverbs" | "meanings" | "englishMeanings";

const STEP_LABELS: Record<string, string> = {
  Uploading: "Uploading",
  "Reading files...": "Reading files...",
  "Validating...": "Validating...",
  "Generating metadata...": "Generating metadata...",
  "Generating embeddings...": "Generating embeddings...",
  "Saving to ChromaDB...": "Saving to ChromaDB...",
  Completed: "Completed",
  Failed: "Failed",
};

const FORMAT_OPTIONS: Array<{ value: DatasetType; label: string; description: string }> = [
  { value: "docx", label: "Microsoft Word (.docx)", description: "Proverbs.docx, Meanings.docx, EnglishMeanings.docx" },
  { value: "txt", label: "Plain Text (.txt)", description: "Proverbs.txt, Meanings.txt, EnglishMeanings.txt" },
];

export function ImportDatasetPage() {
  const [datasetType, setDatasetType] = useState<DatasetType>("docx");
  const [proverbsFile, setProverbsFile] = useState<File | null>(null);
  const [meaningsFile, setMeaningsFile] = useState<File | null>(null);
  const [englishMeaningsFile, setEnglishMeaningsFile] = useState<File | null>(null);
  const [jobProgress, setJobProgress] = useState<ImportJobProgress | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const canUpload = useMemo(
    () => Boolean(proverbsFile && meaningsFile && englishMeaningsFile && !isUploading),
    [proverbsFile, meaningsFile, englishMeaningsFile, isUploading],
  );

  const progressPercent = useMemo(() => {
    if (!jobProgress) return 0;
    if (jobProgress.status === "completed") return 100;
    if (typeof jobProgress.progress === "number") return jobProgress.progress;
    return 0;
  }, [jobProgress]);

  const stepLabel = jobProgress?.step ? STEP_LABELS[jobProgress.step] ?? jobProgress.step : "Ready";
  const extension = datasetType === "docx" ? ".docx" : ".txt";
  const accept =
    datasetType === "docx"
      ? ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      : ".txt,text/plain";

  const clearFiles = () => {
    setProverbsFile(null);
    setMeaningsFile(null);
    setEnglishMeaningsFile(null);
    setJobProgress(null);
  };

  const assignFile = (file: File, kind: FileKind) => {
    if (!file.name.toLowerCase().endsWith(extension)) {
      toast.error("Only DOCX or TXT files are supported.");
      return;
    }
    if (kind === "proverbs") setProverbsFile(file);
    else if (kind === "meanings") setMeaningsFile(file);
    else setEnglishMeaningsFile(file);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>, kind: FileKind) => {
    event.preventDefault();
    const file = event.dataTransfer.files.item(0);
    if (file) assignFile(file, kind);
  };

  const handleUpload = async () => {
    if (!proverbsFile || !meaningsFile || !englishMeaningsFile) return;
    setIsUploading(true);
    setJobProgress(null);
    try {
      const result = await importKnowledge(
        datasetType,
        proverbsFile,
        meaningsFile,
        englishMeaningsFile,
        setJobProgress,
      );

      if (result.status === "failed") {
        toast.error(result.error ?? "Import job failed");
        return;
      }

      toast.success("Dataset imported successfully");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-950">Knowledge Import</h1>
        <p className="mt-2 text-sm text-slate-500">
          Import proverb knowledge into the AI Knowledge Base using Microsoft Word or Plain Text datasets.
        </p>
      </div>

      <section>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-950">Select files</h2>
            <p className="mt-1 text-sm text-slate-500">Use matching files with the same number and order of entries.</p>
          </div>
          <fieldset className="flex w-full rounded-lg border border-slate-200 bg-white p-1 sm:w-auto">
            <legend className="sr-only">Dataset type</legend>
            {FORMAT_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex flex-1 cursor-pointer items-center justify-center rounded-md px-4 py-2 text-sm font-bold transition sm:flex-none ${
                  datasetType === option.value ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-50"
                } ${isUploading ? "cursor-not-allowed opacity-60" : ""}`}
              >
                <input
                  type="radio"
                  name="datasetType"
                  value={option.value}
                  checked={datasetType === option.value}
                  disabled={isUploading}
                  onChange={() => {
                    setDatasetType(option.value);
                    clearFiles();
                  }}
                  className="sr-only"
                />
                {option.value === "docx" ? "Word (.docx)" : "Text (.txt)"}
              </label>
            ))}
          </fieldset>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <UploadBox
          id="proverbs-file"
          label="Proverbs"
          extension={extension}
          accept={accept}
          file={proverbsFile}
          onDrop={(event) => handleDrop(event, "proverbs")}
          onChange={(file) => assignFile(file, "proverbs")}
          onClear={() => setProverbsFile(null)}
          disabled={isUploading}
        />
        <UploadBox
          id="meanings-file"
          label="Myanmar meanings"
          extension={extension}
          accept={accept}
          file={meaningsFile}
          onDrop={(event) => handleDrop(event, "meanings")}
          onChange={(file) => assignFile(file, "meanings")}
          onClear={() => setMeaningsFile(null)}
          disabled={isUploading}
        />
        <UploadBox
          id="english-meanings-file"
          label="English meanings"
          extension={extension}
          accept={accept}
          file={englishMeaningsFile}
          onDrop={(event) => handleDrop(event, "englishMeanings")}
          onChange={(file) => assignFile(file, "englishMeanings")}
          onClear={() => setEnglishMeaningsFile(null)}
          disabled={isUploading}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold text-slate-950">{jobProgress ? "Import progress" : "Ready to import"}</p>
              {jobProgress ? (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                  {stepLabel}
                </span>
              ) : null}
            </div>
            {jobProgress ? <div
              className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"
              role="progressbar"
              aria-label="Dataset import progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPercent}
            >
              <div className="h-full rounded-full bg-brand-600 transition-all duration-300" style={{ width: `${progressPercent}%` }} />
            </div> : <p className="mt-1 text-sm text-slate-500">Choose all three files to enable import.</p>}
            {jobProgress?.total ? (
              <p className="mt-2 text-sm text-slate-500">
                {jobProgress.current ?? 0} / {jobProgress.total}
                {typeof jobProgress.estimated_remaining === "number" && jobProgress.status !== "completed"
                  ? ` - ${jobProgress.estimated_remaining} remaining`
                  : null}
              </p>
            ) : null}
          </div>
          <button type="button" className="btn-primary w-full sm:w-auto" disabled={!canUpload} onClick={handleUpload}>
            {isUploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <UploadCloud className="h-4 w-4" aria-hidden="true" />}
            {isUploading ? "Processing..." : "Knowledge Import"}
          </button>
        </div>
      </div>

      {jobProgress?.status === "completed" ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-900">
          <p className="font-bold">Import complete</p>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ResultStat label="Documents imported" value={jobProgress.documents_imported ?? jobProgress.documents ?? 0} />
            <ResultStat label="Embeddings created" value={jobProgress.embeddings_created ?? jobProgress.documents ?? 0} />
            <ResultStat label="Failed" value={jobProgress.failed ?? 0} />
            <ResultStat label="Seconds" value={jobProgress.processing_time_seconds ?? 0} />
          </dl>
        </div>
      ) : null}

      {jobProgress?.status === "failed" ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-900">
          <p className="font-bold">Import failed</p>
          <p className="mt-2">{jobProgress.error ?? "An unexpected error occurred during import."}</p>
        </div>
      ) : null}
    </div>
  );
}

interface ResultStatProps {
  label: string;
  value: number | string;
}

function ResultStat({ label, value }: ResultStatProps) {
  return (
    <div className="rounded-lg bg-white/70 px-3 py-2">
      <dt className="text-xs font-semibold uppercase text-emerald-700">{label}</dt>
      <dd className="mt-1 text-lg font-bold text-emerald-950">{value}</dd>
    </div>
  );
}

interface UploadBoxProps {
  id: string;
  label: string;
  extension: string;
  accept: string;
  file: File | null;
  disabled?: boolean;
  onDrop: (event: DragEvent<HTMLDivElement>) => void;
  onChange: (file: File) => void;
  onClear: () => void;
}

function UploadBox({ id, label, extension, accept, file, disabled = false, onDrop, onChange, onClear }: UploadBoxProps) {
  return (
    <div
      className={`relative flex min-h-44 flex-col items-center justify-center rounded-xl border border-dashed p-5 text-center transition ${
        file ? "border-emerald-300 bg-emerald-50/50" : "border-slate-300 bg-white"
      } ${
        disabled ? "opacity-60" : "hover:border-brand-300 hover:bg-brand-50/40"
      }`}
      onDragOver={(event) => event.preventDefault()}
      onDrop={disabled ? undefined : onDrop}
    >
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${file ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
        {file ? <CheckCircle2 className="h-6 w-6" aria-hidden="true" /> : <FileText className="h-6 w-6" aria-hidden="true" />}
      </div>
      <span className="mt-3 text-sm font-bold text-slate-950">{label}</span>
      <span className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Required {extension} file</span>
      <input
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          const selected = event.target.files?.item(0);
          if (selected) onChange(selected);
        }}
      />
      {file ? (
        <div className="mt-3 flex w-full max-w-xs items-center gap-2 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700">
          <span className="min-w-0 flex-1">
            <span className="block truncate">{file.name}</span>
            <span className="block text-xs font-normal text-slate-500">{formatFileSize(file.size)}</span>
          </span>
          {!disabled ? (
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                onClear();
              }}
              className="rounded p-1 hover:bg-white"
              aria-label={`Clear ${label}`}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : null}
        </div>
      ) : (
        <label htmlFor={id} className={`mt-3 text-sm font-bold ${disabled ? "cursor-not-allowed text-slate-400" : "cursor-pointer text-brand-700 hover:text-brand-800"}`}>
          Choose file
        </label>
      )}
      {!file ? <span className="mt-2 text-xs text-slate-500">or drag and drop here</span> : null}
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
