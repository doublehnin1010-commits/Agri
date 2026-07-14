import { UploadCloud, X } from "lucide-react";
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

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-950">Knowledge Import</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Import proverb knowledge into the AI Knowledge Base using Microsoft Word or Plain Text datasets.
            </p>
            <p className="mt-4 text-xs font-bold uppercase text-slate-500">Supported formats</p>
            <div className="mt-2 flex flex-wrap gap-2 text-sm font-semibold text-slate-700">
              <span className="rounded bg-slate-100 px-2.5 py-1">Microsoft Word (.docx)</span>
              <span className="rounded bg-slate-100 px-2.5 py-1">Plain Text (.txt)</span>
            </div>
          </div>
          <fieldset className="min-w-full space-y-2 lg:min-w-80">
            <legend className="text-sm font-bold text-slate-950">Dataset type</legend>
            {FORMAT_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${
                  datasetType === option.value ? "border-brand-300 bg-brand-50" : "border-slate-200 hover:bg-slate-50"
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
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-bold text-slate-950">{option.label}</span>
                  <span className="mt-1 block text-xs leading-5 text-slate-500">{option.description}</span>
                </span>
              </label>
            ))}
          </fieldset>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <UploadBox
          label={`Proverbs${extension}`}
          extension={extension}
          accept={accept}
          file={proverbsFile}
          onDrop={(event) => handleDrop(event, "proverbs")}
          onChange={(file) => assignFile(file, "proverbs")}
          onClear={() => setProverbsFile(null)}
          disabled={isUploading}
        />
        <UploadBox
          label={`Meanings${extension}`}
          extension={extension}
          accept={accept}
          file={meaningsFile}
          onDrop={(event) => handleDrop(event, "meanings")}
          onChange={(file) => assignFile(file, "meanings")}
          onClear={() => setMeaningsFile(null)}
          disabled={isUploading}
        />
        <UploadBox
          label={`EnglishMeanings${extension}`}
          extension={extension}
          accept={accept}
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
                  ? ` - ${jobProgress.estimated_remaining} remaining`
                  : null}
              </p>
            ) : null}
          </div>
          <button type="button" className="btn-primary" disabled={!canUpload} onClick={handleUpload}>
            <UploadCloud className="h-4 w-4" aria-hidden="true" />
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
  label: string;
  extension: string;
  accept: string;
  file: File | null;
  disabled?: boolean;
  onDrop: (event: DragEvent<HTMLLabelElement>) => void;
  onChange: (file: File) => void;
  onClear: () => void;
}

function UploadBox({ label, extension, accept, file, disabled = false, onDrop, onChange, onClear }: UploadBoxProps) {
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
      <span className="mt-2 text-sm leading-6 text-slate-500">Drag and drop or browse for a {extension} file</span>
      <input
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
