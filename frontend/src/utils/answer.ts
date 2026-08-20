import type { AiAnswer } from "../types";

export function answerToText(answer: AiAnswer | string | null | undefined): string {
  if (!answer) return "";
  if (typeof answer === "string") return answer;
  return cleanText(answer.answer) ?? cleanText(answer.meaning_simple_mm) ?? cleanText(answer.meaning) ?? JSON.stringify(answer, null, 2);
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
