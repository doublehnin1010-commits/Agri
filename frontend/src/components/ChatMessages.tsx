import {
  BookOpenText,
  GraduationCap,
  HeartHandshake,
  Lightbulb,
  Loader2,
  MessageCircleQuestion,
  Sprout,
  UsersRound,
} from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { ChatBubble } from "./ChatBubble";
import type { HistoryMessage } from "../types/history";
import type { ChatMessage } from "../types";
import { makeId } from "../utils/answer";

interface ChatMessagesProps {
  messages: HistoryMessage[];
  isResponding?: boolean;
  onStarterClick?: (text: string) => void | Promise<unknown>;
  showStarterSuggestions?: boolean;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
}

const STARTER_PROMPTS = [
  {
    icon: BookOpenText,
    label: "Explain a proverb",
    prompt: "Explain a Myanmar proverb in a simple way",
  },
  {
    icon: HeartHandshake,
    label: "About kindness",
    prompt: "Tell me a Myanmar proverb about kindness",
  },
  {
    icon: GraduationCap,
    label: "About learning",
    prompt: "Give me a Myanmar proverb about learning",
  },
  {
    icon: MessageCircleQuestion,
    label: "မြန်မာလိုမေးမယ်",
    prompt: "စိတ်ရှည်မှုအကြောင်း မြန်မာစကားပုံတစ်ခု ပြောပြပါ",
  },
  {
    icon: Lightbulb,
    label: "Life advice",
    prompt: "Give me a Myanmar proverb with useful life advice",
  },
  {
    icon: UsersRound,
    label: "About friendship",
    prompt: "Tell me a Myanmar proverb about friendship",
  },
  {
    icon: Sprout,
    label: "About patience",
    prompt: "Explain a Myanmar proverb about patience",
  },
  {
    icon: BookOpenText,
    label: "စကားပုံရှာမယ်",
    prompt: "ကြိုးစားမှုအကြောင်း မြန်မာစကားပုံတစ်ခု ရှင်းပြပါ",
  },
];

function getRandomStarterPrompts() {
  return [...STARTER_PROMPTS]
    .sort(() => Math.random() - 0.5)
    .slice(0, 4);
}

export function ChatMessages({
  messages,
  isResponding = false,
  onStarterClick,
  showStarterSuggestions = true,
  emptyStateTitle = "What proverb shall we learn today?",
  emptyStateDescription = "Ask in English or Myanmar. I'll explain it simply, like a friendly teacher.",
}: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const starterPrompts = useMemo(getRandomStarterPrompts, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isResponding]);

  if (!messages.length) {
    return (
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center py-8">
        <div className="rounded-lg border border-slate-200 bg-white px-5 py-8 text-center shadow-sm sm:px-8">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <BookOpenText className="h-7 w-7" aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-xl font-bold text-slate-950 sm:text-2xl">{emptyStateTitle}</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-500">{emptyStateDescription}</p>
        </div>
        {showStarterSuggestions && onStarterClick ? (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {starterPrompts.map(({ icon: Icon, label, prompt }) => (
              <button
                key={prompt}
                type="button"
                onClick={() => void onStarterClick(prompt)}
                disabled={isResponding}
                className="group flex min-h-16 items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-left shadow-sm transition hover:border-brand-300 hover:bg-brand-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600 transition group-hover:bg-white group-hover:text-brand-700">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-bold leading-5 text-slate-800">{label}</span>
                  <span className="mt-0.5 block text-xs leading-5 text-slate-500">{prompt}</span>
                </span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      {messages.map((message) => (
        <ChatBubble key={message.id ?? makeId("message")} message={toChatMessage(message)} />
      ))}
      {isResponding ? (
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-500 shadow-sm">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          </span>
          <span>Thinking through the proverb...</span>
        </div>
      ) : null}
      <div ref={scrollRef} />
    </div>
  );
}

function toChatMessage(message: HistoryMessage): ChatMessage {
  return {
    id: message.id ?? makeId("message"),
    role: message.role,
    content: message.content,
    answer: message.answer,
    createdAt: message.created_at ?? new Date().toISOString(),
  };
}
