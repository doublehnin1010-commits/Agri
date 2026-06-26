import { BookOpenText, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
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



export function ChatMessages({
  messages,
  isResponding = false,
  onStarterClick,
  showStarterSuggestions = true,
  emptyStateTitle = "Start a proverb conversation",
  emptyStateDescription = "Use English or Myanmar Unicode to ask for meanings, examples, comparisons, or study guidance.",
}: ChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isResponding]);

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
          AI is preparing an answer...
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
