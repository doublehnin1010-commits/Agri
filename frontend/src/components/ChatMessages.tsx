import { BookOpenText, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ChatBubble } from "./ChatBubble";
import { EmptyState } from "./EmptyState";
import type { HistoryMessage } from "../types/history";
import type { ChatMessage } from "../types";
import { makeId } from "../utils/answer";

interface ChatMessagesProps {
  messages: HistoryMessage[];
  isResponding?: boolean;
  onStarterClick?: (text: string) => void;
  showStarterSuggestions?: boolean;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
}

// Updated with the more formal English phrases you requested earlier
const LOADING_PHRASES = [
  "Understanding your request...",
  "Searching the knowledge base...",
  "Retrieving relevant proverbs...",
  "Analyzing contextual information...",
  "Reasoning over the retrieved knowledge...",
  "Generating a comprehensive response...",
  "Finalizing your answer..."
];

export function ChatMessages({
  messages,
  isResponding = false,
  onStarterClick,
  showStarterSuggestions = true,
  emptyStateTitle = "Start a proverb conversation",
  emptyStateDescription = "Use English or Myanmar Unicode to ask for meanings, examples, comparisons, or study guidance.",
}: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [phraseIndex, setPhraseIndex] = useState(0);

  // 1. Smoothly autoscroll whenever messages or status changes
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isResponding]);

  // 2. Cycle through phrases while waiting for a response without flickering
  useEffect(() => {
    if (!isResponding) {
      setPhraseIndex(0); // Reset to first phrase when done loading
      return;
    }

    const interval = setInterval(() => {
      setPhraseIndex((prevIndex) => (prevIndex + 1) % LOADING_PHRASES.length);
    }, 3000); // Transitions to the next formal phrase every 3 seconds

    return () => clearInterval(interval);
  }, [isResponding]);

  if (!messages.length) {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-5 py-10">
        <EmptyState
          icon={BookOpenText}
          title={emptyStateTitle}
          description={emptyStateDescription}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5">
      {messages.map((message) => (
        <ChatBubble key={message.id ?? makeId("message")} message={toChatMessage(message)} />
      ))}
      {isResponding ? (
        <div className="flex items-center gap-3 text-sm font-semibold text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {/* Fixed: Use the controlled phrase index instead of direct Math.random() */}
          <span>{LOADING_PHRASES[phraseIndex]}</span>
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