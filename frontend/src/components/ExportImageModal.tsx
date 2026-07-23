import { Copy, Download, FileImage, Image as ImageIcon, Loader2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import type { AiAnswer, SourceItem } from "../types";
import {
  blobToObjectUrl,
  copyBlobToClipboard,
  downloadBlob,
  type ExportImageFormat,
  renderElementToBlob,
} from "../utils/exportImage";

interface ExportImageModalProps {
  answer: AiAnswer;
  onClose: () => void;
}

type ExportContent =
  | {
      type: "single";
      proverb: string;
      meaning?: string;
      englishMeaning?: string;
    }
  | {
      type: "related";
      items: string[];
    };

export function canExportAnswer(answer: AiAnswer | undefined): answer is AiAnswer {
  if (!answer) return false;
  if (typeof answer.proverb === "string" && answer.proverb.trim()) return true;
  return getRelatedProverbs(answer).length > 1;
}

export function ExportImageModal({ answer, onClose }: ExportImageModalProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(true);
  const [isCopying, setIsCopying] = useState(false);
  const [isDownloading, setIsDownloading] = useState<ExportImageFormat | null>(null);
  const content = useMemo(() => getExportContent(answer), [answer]);

  useEffect(() => {
    let isMounted = true;
    let nextUrl: string | null = null;

    async function renderPreview() {
      if (!cardRef.current) return;
      setIsRendering(true);
      try {
        const blob = await renderElementToBlob(cardRef.current, "png");
        nextUrl = blobToObjectUrl(blob);
        if (isMounted) setPreviewUrl(nextUrl);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Unable to render image preview.");
      } finally {
        if (isMounted) setIsRendering(false);
      }
    }

    void renderPreview();

    return () => {
      isMounted = false;
      if (nextUrl) URL.revokeObjectURL(nextUrl);
    };
  }, [content]);

  const createBlob = async (format: ExportImageFormat) => {
    if (!cardRef.current) {
      throw new Error("Export card is not ready yet.");
    }
    return renderElementToBlob(cardRef.current, format);
  };

  const handleDownload = async (format: ExportImageFormat) => {
    setIsDownloading(format);
    try {
      const blob = await createBlob(format);
      downloadBlob(blob, `myanmar-proverb-card.${format === "jpeg" ? "jpg" : "png"}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to download image.");
    } finally {
      setIsDownloading(null);
    }
  };

  const handleCopy = async () => {
    setIsCopying(true);
    try {
      const blob = await createBlob("png");
      await copyBlobToClipboard(blob);
      toast.success("Image copied to clipboard.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to copy image.");
    } finally {
      setIsCopying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-soft">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
              <ImageIcon className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-base font-bold text-slate-950">Export Image</h2>
              <p className="text-xs text-slate-500">1080 x 1350 share card</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="btn-secondary px-3" aria-label="Close export preview">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="grid min-h-0 flex-1 gap-5 overflow-y-auto bg-slate-50 p-4 lg:grid-cols-[minmax(0,1fr)_260px]">
          <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-slate-200 bg-white p-4">
            {previewUrl && !isRendering ? (
              <img
                src={previewUrl}
                alt="Export preview"
                className="max-h-[68vh] w-auto max-w-full rounded-lg border border-slate-200 shadow-soft"
              />
            ) : (
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Rendering preview...
              </div>
            )}
          </div>

          <div className="flex flex-col gap-3">
            <button
              type="button"
              className="btn-primary w-full"
              disabled={isRendering || isDownloading !== null}
              onClick={() => void handleDownload("png")}
            >
              {isDownloading === "png" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              Download PNG
            </button>
            <button
              type="button"
              className="btn-secondary w-full"
              disabled={isRendering || isDownloading !== null}
              onClick={() => void handleDownload("jpeg")}
            >
              {isDownloading === "jpeg" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileImage className="h-4 w-4" />}
              Download JPEG
            </button>
            <button
              type="button"
              className="btn-secondary w-full"
              disabled={isRendering || isCopying}
              onClick={() => void handleCopy()}
            >
              {isCopying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Copy className="h-4 w-4" />}
              Copy Image
            </button>
          </div>
        </div>
      </div>

      <div className="pointer-events-none fixed -left-[12000px] top-0" aria-hidden="true">
        <ExportCard ref={cardRef} content={content} />
      </div>
    </div>
  );
}

const ExportCard = ({
  content,
  ref,
}: {
  content: ExportContent;
  ref: React.Ref<HTMLDivElement>;
}) => {
  const isRelated = content.type === "related";

  return (
    <div
      ref={ref}
      style={{
        width: 1080,
        height: 1350,
        boxSizing: "border-box",
        background: "linear-gradient(145deg, #f8fafc 0%, #eef2ff 100%)",
        color: "#111827",
        fontFamily: "'Noto Sans Myanmar', Inter, Arial, sans-serif",
        padding: 72,
      }}
    >
      <div
        style={{
          display: "flex",
          height: "100%",
          flexDirection: "column",
          border: "1px solid #e5e7eb",
          borderRadius: 30,
          background: "rgba(255, 255, 255, 0.94)",
          boxShadow: "0 26px 80px rgba(15, 23, 42, 0.12)",
          padding: 58,
        }}
      >
        <div style={{ color: "#4f46e5", fontSize: 30, fontWeight: 700, lineHeight: 1.5 }}>
          {isRelated ? "Related Proverbs" : "📖 Myanmar Proverb"}
        </div>

        <div
          style={{
            marginTop: 32,
            borderTop: "1px solid #e5e7eb",
            paddingTop: 40,
            flex: 1,
            overflow: "hidden",
          }}
        >
          {content.type === "single" ? <SingleProverbContent content={content} /> : <RelatedProverbsContent items={content.items} />}
        </div>

        <div
          style={{
            borderTop: "1px solid #e5e7eb",
            color: "#64748b",
            fontSize: 24,
            fontWeight: 600,
            lineHeight: 1.5,
            paddingTop: 28,
          }}
        >
          Generated by
          <br />
          <span style={{ color: "#111827" }}>Myanmar Proverbs AI Assistant</span>
        </div>
      </div>
    </div>
  );
};

function SingleProverbContent({ content }: { content: Extract<ExportContent, { type: "single" }> }) {
  return (
    <div style={{ display: "flex", height: "100%", flexDirection: "column", gap: 34 }}>
      <div
        style={{
          color: "#0f172a",
          fontSize: fitText(content.proverb, 58, 46),
          fontWeight: 700,
          lineHeight: 1.65,
          whiteSpace: "pre-wrap",
          overflowWrap: "break-word",
        }}
      >
        {content.proverb}
      </div>
      {content.meaning ? <TextSection title="Meaning" text={content.meaning} /> : null}
      {content.englishMeaning ? <TextSection title="English Meaning" text={content.englishMeaning} /> : null}
    </div>
  );
}

function RelatedProverbsContent({ items }: { items: string[] }) {
  return (
    <div style={{ display: "flex", height: "100%", flexDirection: "column", gap: 28 }}>
      <div style={{ color: "#0f172a", fontSize: 58, fontWeight: 800, lineHeight: 1.35 }}>
        Related Proverbs
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        {items.slice(0, 5).map((item, index) => (
          <div
            key={`${item}-${index}`}
            style={{
              display: "grid",
              gridTemplateColumns: "36px 1fr",
              gap: 18,
              color: "#1f2937",
              fontSize: fitText(item, 37, 30),
              fontWeight: 600,
              lineHeight: 1.7,
              overflowWrap: "break-word",
            }}
          >
            <span style={{ color: "#4f46e5" }}>•</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TextSection({ title, text }: { title: string; text: string }) {
  return (
    <div
      style={{
        borderTop: "1px solid #e5e7eb",
        paddingTop: 28,
      }}
    >
      <div style={{ color: "#4f46e5", fontSize: 24, fontWeight: 700, lineHeight: 1.4 }}>{title}</div>
      <div
        style={{
          marginTop: 14,
          color: "#334155",
          fontSize: fitText(text, 32, 24),
          fontWeight: 500,
          lineHeight: 1.8,
          whiteSpace: "pre-wrap",
          overflowWrap: "break-word",
        }}
      >
        {text}
      </div>
    </div>
  );
}

function getExportContent(answer: AiAnswer): ExportContent {
  const proverb = cleanText(answer.proverb);
  if (proverb) {
    return {
      type: "single",
      proverb,
      meaning: cleanText(answer.meaning_simple_mm) ?? cleanText(answer.meaning),
      englishMeaning: cleanText(answer.english_meaning) ?? cleanText(answer.sources?.[0]?.english_meaning),
    };
  }

  return {
    type: "related",
    items: getRelatedProverbs(answer),
  };
}

function getRelatedProverbs(answer: AiAnswer): string[] {
  const sourceItems = (answer.sources ?? [])
    .map((source: SourceItem) => cleanText(source.proverb))
    .filter((item): item is string => Boolean(item));

  if (sourceItems.length > 1 || answer.intent === "proverb_list") {
    return Array.from(new Set(sourceItems)).slice(0, 5);
  }

  return [];
}

function cleanText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function fitText(text: string, normalSize: number, compactSize: number): number {
  return text.length > 220 ? compactSize : text.length > 140 ? Math.round((normalSize + compactSize) / 2) : normalSize;
}
