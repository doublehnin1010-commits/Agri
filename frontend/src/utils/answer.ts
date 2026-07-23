import type { AiAnswer } from "../types";

export function answerToText(answer: AiAnswer | string | null | undefined): string {
  if (!answer) return "";
  if (typeof answer === "string") return answer;

  const proverb = cleanText(answer.proverb);
  const meaning = cleanText(answer.meaning_simple_mm) ?? cleanText(answer.meaning);
  const example = cleanText(answer.example_mm) ?? cleanText(answer.example);
  const isEnglish = answer.language === "en" || looksEnglish(meaning);

  if (answer.intent === "proverb_list") {
    return [meaning, example].filter(Boolean).join("\n\n");
  }

  if (!proverb) {
    const fallback = [meaning, example].filter(Boolean).join("\n\n");
    if (fallback) return fallback;
  }

  if (isEnglish) {
    return [
      proverb ? `Proverb:\n${proverb}` : null,
      meaning ? `Meaning:\n${meaning}` : null,
      example ? `Example:\n${example}` : null,
    ].filter(Boolean).join("\n\n");
  }

  const parts = [
    proverb ? `စကားပုံ:\n${proverb}` : null,
    meaning ? `အဓိပ္ပါယ်:\n${meaning}` : null,
    example ? `ဥပမာ:\n${example}` : null,
  ].filter(Boolean);

  if (parts.length) return parts.join("\n\n");
  return JSON.stringify(answer, null, 2);
}

export function formatDate(value: string | number | Date): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function makeId(prefix = "id"): string {
  return `${prefix}-${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)}`;
}

function cleanText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function looksEnglish(value: string | null): boolean {
  if (!value) return false;
  const latin = (value.match(/[A-Za-z]/g) ?? []).length;
  const myanmar = (value.match(/[\u1000-\u109F]/g) ?? []).length;
  return latin > 0 && latin >= myanmar;
}
