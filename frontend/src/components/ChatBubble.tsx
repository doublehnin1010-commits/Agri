import { BookOpenText, Bot, GraduationCap, Lightbulb, MessageSquareText, UserRound } from "lucide-react";
import type { ChatMessage } from "../types";
import { FavoriteButton } from "./FavoriteButton";

interface ChatBubbleProps {
  message: ChatMessage;
}

interface AnswerSections {
  proverb: string | null;
  meaning: string | null;
  lesson: string | null;
  example: string | null;
}

const SECTION_PATTERN = /(?:^|\n)\s*(စကားပုံ|အဓိပ္ပါယ်|သင်ခန်းစာ|ဥပမာ|Proverb|Meaning|Lesson|Example)\s*[:：]\s*/g;

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const answerProverb = cleanText(message.answer?.proverb);
  const rawMeaning = cleanText(message.answer?.meaning_simple_mm) ?? cleanText(message.answer?.meaning);
  const answerExample = cleanText(message.answer?.example_mm) ?? cleanText(message.answer?.example);
  const sections = parseAnswerSections(rawMeaning);
  const proverb = answerProverb ?? sections.proverb;
  const proverbId =
    cleanText(message.answer?.proverb_id) ??
    cleanText(message.answer?.sources?.find((source) => cleanText(source.proverb) === proverb)?.id) ??
    cleanText(message.answer?.sources?.[0]?.id);
  const example = sections.example ?? answerExample;
  const isProverbList = message.answer?.intent === "proverb_list";
  const isEnglish = message.answer?.language === "en" || looksEnglish(rawMeaning);
  const hasStructuredAnswer = !isUser && Boolean(proverb);

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white shadow-sm">
          <Bot className="h-5 w-5" aria-hidden="true" />
        </div>
      ) : null}

      <div
        className={`text-sm leading-7 ${
          isUser
            ? "max-w-[min(680px,85%)] rounded-lg bg-brand-600 px-4 py-3 text-white shadow-sm"
            : "min-w-0 flex-1 rounded-lg border border-cream-200 bg-cream-50 px-5 py-5 text-slate-800 shadow-sm sm:px-6"
        }`}
      >
        {isProverbList ? (
          <div className="space-y-4">
            {message.answer?.sources?.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {message.answer.sources
                  .filter((source) => source.proverb)
                  .map((source, index) => {
                    const sourceId = cleanText(source.id);
                    return (
                      <article key={sourceId ?? `${source.proverb}-${index}`} className="rounded-lg border border-cream-200 bg-white p-4 shadow-sm">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-brand-700">Proverb {index + 1}</p>
                            <h3 className="mt-1 break-words text-base font-bold leading-7 text-slate-950">{source.proverb}</h3>
                          </div>
                          {sourceId ? <FavoriteButton proverbId={sourceId} compact /> : null}
                        </div>
                        <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-600">
                          {source.meaning || source.english_meaning || "No meaning available."}
                        </p>
                      </article>
                    );
                  })}
              </div>
            ) : rawMeaning ? (
              <p className="whitespace-pre-wrap text-[15px] leading-8">{rawMeaning}</p>
            ) : null}
            {answerExample ? <p className="whitespace-pre-wrap text-[15px] leading-8 text-slate-600">{answerExample}</p> : null}
          </div>
        ) : hasStructuredAnswer ? (
          <article>
            <header className="flex flex-col gap-3 border-b border-cream-200 pb-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex min-w-0 items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
                <BookOpenText className="h-5 w-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-xs font-bold text-brand-700">{isEnglish ? "Proverb" : "စကားပုံ"}</p>
                <h3 className="mt-1 break-words text-lg font-bold leading-8 text-slate-950">{proverb}</h3>
              </div>
              </div>
              {proverbId ? <FavoriteButton proverbId={proverbId} compact /> : null}
            </header>

            <div className="divide-y divide-cream-200">
              <AnswerSection icon={MessageSquareText} label={isEnglish ? "Meaning" : "အဓိပ္ပါယ်"} text={sections.meaning} />
              <AnswerSection icon={Lightbulb} label={isEnglish ? "Lesson" : "သင်ခန်းစာ"} text={sections.lesson} />
              <AnswerSection icon={GraduationCap} label={isEnglish ? "Example" : "ဥပမာ"} text={example} />
            </div>
          </article>
        ) : (
          <p className="whitespace-pre-wrap text-[15px] leading-8">{message.content}</p>
        )}
      </div>

      {isUser ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-700">
          <UserRound className="h-5 w-5" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  );
}

function AnswerSection({
  icon: Icon,
  label,
  text,
}: {
  icon: typeof MessageSquareText;
  label: string;
  text: string | null;
}) {
  if (!text) return null;

  return (
    <section className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-3 py-4 last:pb-0">
      <Icon className="mt-1 h-5 w-5 text-brand-700" aria-hidden="true" />
      <div className="min-w-0">
        <h4 className="text-sm font-bold text-slate-950">{label}</h4>
        <p className="mt-1 whitespace-pre-wrap break-words text-[15px] leading-8 text-slate-700">{text}</p>
      </div>
    </section>
  );
}

function parseAnswerSections(text: string | null): AnswerSections {
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

    if (label === "စကားပုံ" || label === "Proverb") result.proverb = value;
    if (label === "အဓိပ္ပါယ်" || label === "Meaning") result.meaning = value;
    if (label === "သင်ခန်းစာ" || label === "Lesson") result.lesson = value;
    if (label === "ဥပမာ" || label === "Example") result.example = value;
  }

  return result;
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
