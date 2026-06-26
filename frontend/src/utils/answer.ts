import type { AiAnswer } from "../types";

export function answerToText(answer: AiAnswer | string | null | undefined): string {
  if (!answer) return "";
  if (typeof answer === "string") return answer;

  const parts = [
    answer.proverb,
    answer.meaning_simple_mm ?? answer.meaning,
    answer.example_mm ?? answer.example,
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
