import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ImagePlus, Loader2, RefreshCw, UploadCloud } from "lucide-react";
import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getApiErrorMessage } from "../../api/client";
import { importImageLibraryRecords, listImageLibraryRecords } from "../../services/imageLibraryService";
import type { ImageLibraryPayload } from "../../types";

const SAMPLE_LIBRARY_JSON = `[
  {
    "title": "စကားပုံ",
    "prompt": "Stored prompt exactly as saved.",
    "image_files": [
      "proverbs/example-1.png",
      "proverbs/example-2.png",
      "proverbs/example-3.png"
    ]
  }
]`;

export function ImageLibraryImportPage() {
  const queryClient = useQueryClient();
  const [jsonText, setJsonText] = useState(SAMPLE_LIBRARY_JSON);

  const { data: records = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ["image-library"],
    queryFn: listImageLibraryRecords,
    retry: false,
  });

  const parsedRecords = useMemo(() => parseLibraryJson(jsonText), [jsonText]);
  const canImport = parsedRecords.ok && parsedRecords.records.length > 0;

  const importMutation = useMutation({
    mutationFn: importImageLibraryRecords,
    onSuccess: (result) => {
      toast.success(`${result.imported} image library record imported`);
      queryClient.invalidateQueries({ queryKey: ["image-library"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const handleImport = () => {
    if (!parsedRecords.ok) {
      toast.error(parsedRecords.error);
      return;
    }
    importMutation.mutate(parsedRecords.records);
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-950">Image Library Import</h1>
          <p className="mt-2 text-sm text-slate-500">
            Import saved proverb prompts and local image paths for dashboard image selection.
          </p>
        </div>
        <button type="button" className="btn-secondary w-full sm:w-auto" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh
        </button>
      </header>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-950">Seed JSON</h2>
              <p className="mt-1 text-sm text-slate-500">Paths must be relative to backend/library_images.</p>
            </div>
            <button
              type="button"
              className="btn-secondary w-full sm:w-auto"
              onClick={() => setJsonText(SAMPLE_LIBRARY_JSON)}
              disabled={importMutation.isPending}
            >
              Use sample
            </button>
          </div>

          <label className="sr-only" htmlFor="image-library-json">
            Image library JSON
          </label>
          <textarea
            id="image-library-json"
            value={jsonText}
            onChange={(event) => setJsonText(event.target.value)}
            disabled={importMutation.isPending}
            spellCheck={false}
            className="mt-4 min-h-[24rem] w-full resize-y rounded-lg border border-slate-200 bg-slate-950 px-4 py-3 font-mono text-sm leading-6 text-slate-50 outline-none transition placeholder:text-slate-500 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-60"
          />

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <ImportStatus parsedRecords={parsedRecords} />
            <button
              type="button"
              className="btn-primary w-full sm:w-auto"
              onClick={handleImport}
              disabled={!canImport || importMutation.isPending}
            >
              {importMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <UploadCloud className="h-4 w-4" aria-hidden="true" />
              )}
              {importMutation.isPending ? "Importing..." : "Import Images"}
            </button>
          </div>
        </div>

        <aside className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
              <ImagePlus className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-950">Library records</h2>
              <p className="text-sm text-slate-500">{isLoading ? "Loading..." : `${records.length} records`}</p>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {records.slice(0, 8).map((record) => (
              <div key={record.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="truncate text-sm font-bold text-slate-950">{record.title}</p>
                <p className="mt-1 text-xs font-semibold text-slate-500">{record.image_files.length} images</p>
              </div>
            ))}
            {!isLoading && !records.length ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                No image library records yet.
              </div>
            ) : null}
          </div>
        </aside>
      </section>
    </div>
  );
}

type ParseResult =
  | { ok: true; records: ImageLibraryPayload[] }
  | { ok: false; error: string; records: ImageLibraryPayload[] };

function parseLibraryJson(value: string): ParseResult {
  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) {
      return { ok: false, error: "JSON must be an array of image library records.", records: [] };
    }

    const records = parsed.map((item, index) => {
      if (!item || typeof item !== "object") {
        throw new Error(`Record ${index + 1} must be an object.`);
      }
      const record = item as Partial<ImageLibraryPayload>;
      if (typeof record.title !== "string" || !record.title.trim()) {
        throw new Error(`Record ${index + 1} needs a title.`);
      }
      if (typeof record.prompt !== "string" || !record.prompt.trim()) {
        throw new Error(`Record ${index + 1} needs a prompt.`);
      }
      if (!Array.isArray(record.image_files) || record.image_files.length === 0) {
        throw new Error(`Record ${index + 1} needs at least one image file.`);
      }
      const imageFiles = record.image_files.map((path, pathIndex) => {
        if (typeof path !== "string" || !path.trim()) {
          throw new Error(`Record ${index + 1}, image ${pathIndex + 1} must be a path string.`);
        }
        return path.trim();
      });
      return {
        title: record.title.trim(),
        prompt: record.prompt.trim(),
        image_files: imageFiles,
      };
    });

    return { ok: true, records };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "Invalid JSON.",
      records: [],
    };
  }
}

function ImportStatus({ parsedRecords }: { parsedRecords: ParseResult }) {
  if (!parsedRecords.ok) {
    return <p className="text-sm font-semibold text-red-700">{parsedRecords.error}</p>;
  }

  return (
    <p className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700">
      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
      {parsedRecords.records.length} records ready
    </p>
  );
}
