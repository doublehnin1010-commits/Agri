import { UploadCloud, X } from "lucide-react";
import { DragEvent, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../../api/client";
import { importDocx } from "../../services/uploadService";
import type { ImportJobProgress } from "../../types";

type FileKind = "proverbs" | "meanings" | "englishMeanings";

const STEP_LABELS: Record<string, string> = {
  Uploading: "Uploading",
  "Reading DOCX": "Reading DOCX",
  "Validating Paragraph Counts": "Validating files",
  "Generating Metadata": "Generating Metadata",
  Embedding: "Embedding",
  "Saving to ChromaDB": "Saving to ChromaDB",
  Completed: "Completed",
  Failed: "Failed",
};

export function ImportDatasetPage() {
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

  const assignFile = (file: File, kind: FileKind) => {
    if (!file.name.toLowerCase().endsWith(".docx")) {
      toast.error("Only .docx files are supported");
      return;
    }
    if (kind === "proverbs") setProverbsFile(file);
    else if (kind === "meanings") setMeaningsFile(file);
    else setEnglishMeaningsFile(file);
  };

  const handleDrop = (event: DragEvent<HTMLLabelElement>, kind: FileKind) => {
    event.preventDefault();
    const file = event.dataTransfer.files.item(0);
    if (file) assignFile(file, kind);
  };

  const handleUpload = async () => {
    if (!proverbsFile || !meaningsFile || !englishMeaningsFile) return;
    setIsUploading(true);
    setJobProgress(null);
    try {
      const result = await importDocx(
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
        <h1 className="text-2xl font-bold text-slate-950">Import Dataset</h1>
        <p className="mt-2 text-sm text-slate-500">
          Upload matching proverb, Myanmar meaning, and English meaning Word documents.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <UploadBox
          label="Proverbs.docx"
          file={proverbsFile}
          onDrop={(event) => handleDrop(event, "proverbs")}
          onChange={(file) => assignFile(file, "proverbs")}
          onClear={() => setProverbsFile(null)}
          disabled={isUploading}
        />
        <UploadBox
          label="Meanings.docx"
          file={meaningsFile}
          onDrop={(event) => handleDrop(event, "meanings")}
          onChange={(file) => assignFile(file, "meanings")}
          onClear={() => setMeaningsFile(null)}
          disabled={isUploading}
        />
        <UploadBox
          label="EnglishMeanings.docx"
          file={englishMeaningsFile}
          onDrop={(event) => handleDrop(event, "englishMeanings")}
          onChange={(file) => assignFile(file, "englishMeanings")}
          onClear={() => setEnglishMeaningsFile(null)}
          disabled={isUploading}
        />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold text-slate-950">Import progress</p>
              {jobProgress ? (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                  {stepLabel}
                </span>
              ) : null}
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full bg-brand-600 transition-all" style={{ width: `${progressPercent}%` }} />
            </div>
            {jobProgress?.total ? (
              <p className="mt-2 text-sm text-slate-500">
                {jobProgress.current ?? 0} / {jobProgress.total}
                {typeof jobProgress.estimated_remaining === "number" && jobProgress.status !== "completed"
                  ? ` · ${jobProgress.estimated_remaining} remaining`
                  : null}
              </p>
            ) : null}
          </div>
          <button type="button" className="btn-primary" disabled={!canUpload} onClick={handleUpload}>
            <UploadCloud className="h-4 w-4" aria-hidden="true" />
            {isUploading ? "Processing..." : "Import Dataset"}
          </button>
        </div>
      </div>

      {jobProgress?.status === "completed" ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-900">
          <p className="font-bold">Import complete</p>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ResultStat label="Documents" value={jobProgress.documents ?? 0} />
            <ResultStat label="Metadata failed" value={jobProgress.failed ?? 0} />
            <ResultStat label="Seconds" value={jobProgress.processing_time_seconds ?? 0} />
            <ResultStat label="Job ID" value={jobProgress.job_id.slice(0, 8)} />
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
  label: string;
  file: File | null;
  disabled?: boolean;
  onDrop: (event: DragEvent<HTMLLabelElement>) => void;
  onChange: (file: File) => void;
  onClear: () => void;
}

function UploadBox({ label, file, disabled = false, onDrop, onChange, onClear }: UploadBoxProps) {
  return (
    <label
      className={`flex min-h-56 flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-white p-6 text-center shadow-sm transition ${
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-brand-300 hover:bg-brand-50"
      }`}
      onDragOver={(event) => event.preventDefault()}
      onDrop={disabled ? undefined : onDrop}
    >
      <UploadCloud className="h-10 w-10 text-brand-700" aria-hidden="true" />
      <span className="mt-4 text-base font-bold text-slate-950">{label}</span>
      <span className="mt-2 text-sm leading-6 text-slate-500">Drag and drop or browse for a .docx file</span>
      <input
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          const selected = event.target.files?.item(0);
          if (selected) onChange(selected);
        }}
      />
      {file ? (
        <span className="mt-4 inline-flex max-w-full items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">
          <span className="truncate">{file.name}</span>
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
        </span>
      ) : null}
    </label>
  );
}
