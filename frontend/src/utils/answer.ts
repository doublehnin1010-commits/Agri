import type { AiAnswer } from "../types";

export interface AnswerSections {
  proverb: string | null;
  meaning: string | null;
  lesson: string | null;
  example: string | null;
}

const LABELS = {
  proverbMm: "\u1005\u1000\u102c\u1038\u1015\u102f\u1036",
  meaningMm: "\u1021\u1013\u102d\u1015\u1039\u1015\u102b\u101a\u103a",
  lessonMm: "\u101e\u1004\u103a\u1001\u1014\u103a\u1038\u1005\u102c",
  exampleMm: "\u1025\u1015\u1019\u102c",
} as const;

const SECTION_PATTERN = new RegExp(
  `(?:^|\\n)\\s*(${[
    LABELS.proverbMm,
    LABELS.meaningMm,
    LABELS.lessonMm,
    LABELS.exampleMm,
    "Proverb",
    "Meaning",
    "Lesson",
    "Example",
  ].join("|")})\\s*[:\uff1a]\\s*`,
  "g",
);

export function answerToText(answer: AiAnswer | string | null | undefined): string {
  if (!answer) return "";
  if (typeof answer === "string") return answer;

  const sections = getAnswerSections(answer);
  const { proverb, meaning, lesson, example } = sections;
  const isEnglish = answer.language === "en" || looksEnglish(meaning);

  if (answer.intent === "proverb_list") {
    return cleanText(answer.meaning_simple_mm) ?? [meaning, lesson, example].filter(Boolean).join("\n\n");
  }

  if (!proverb) {
    const fallback = [meaning, lesson, example].filter(Boolean).join("\n\n");
    if (fallback) return fallback;
  }

  const labels = getAnswerLabels(isEnglish);
  const parts = [
    proverb ? `${labels.proverb}:\n${proverb}` : null,
    meaning ? `${labels.meaning}:\n${meaning}` : null,
    lesson ? `${labels.lesson}:\n${lesson}` : null,
    example ? `${labels.example}:\n${example}` : null,
  ].filter(Boolean);

  if (parts.length) return parts.join("\n\n");
  return JSON.stringify(answer, null, 2);
}

export function getAnswerSections(answer: AiAnswer | null | undefined): AnswerSections {
  const rawMeaning = cleanText(answer?.meaning_simple_mm) ?? cleanText(answer?.meaning);
  const sections = parseAnswerSections(rawMeaning);
  const example = cleanText(answer?.example_mm) ?? cleanText(answer?.example);
  return {
    proverb: cleanText(answer?.proverb) ?? sections.proverb,
    meaning: sections.meaning,
    lesson: sections.lesson,
    example: sections.example ?? example,
  };
}

export function parseAnswerSections(text: string | null): AnswerSections {
  const result: AnswerSections = { proverb: null, meaning: null, lesson: null, example: null };
  if (!text) return result;

  const matches = [...text.matchAll(SECTION_PATTERN)];
  if (!matches.length) {
    result.meaning = text;
    return result;
  }

  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const label = match[1];
    const start = (match.index ?? 0) + match[0].length;
    const end = matches[index + 1]?.index ?? text.length;
    const value = cleanText(text.slice(start, end));

    if (label === LABELS.proverbMm || label === "Proverb") result.proverb = value;
    if (label === LABELS.meaningMm || label === "Meaning") result.meaning = value;
    if (label === LABELS.lessonMm || label === "Lesson") result.lesson = value;
    if (label === LABELS.exampleMm || label === "Example") result.example = value;
  }

  return result;
}

export function getAnswerLabels(isEnglish: boolean) {
  return {
    proverb: isEnglish ? "Proverb" : LABELS.proverbMm,
    meaning: isEnglish ? "Meaning" : LABELS.meaningMm,
    lesson: isEnglish ? "Lesson" : LABELS.lessonMm,
    example: isEnglish ? "Example" : LABELS.exampleMm,
  };
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

export function looksEnglish(value: string | null): boolean {
  if (!value) return false;
  const latin = (value.match(/[A-Za-z]/g) ?? []).length;
  const myanmar = (value.match(/[\u1000-\u109F]/g) ?? []).length;
  return latin > 0 && latin >= myanmar;
}
