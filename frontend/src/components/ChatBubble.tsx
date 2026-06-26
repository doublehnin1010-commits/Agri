import { Bot, UserRound } from "lucide-react";
import type { ChatMessage } from "../types";

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
          <Bot className="h-5 w-5" aria-hidden="true" />
        </div>
      ) : null}

      <div
        className={`max-w-[min(760px,85%)] rounded-lg px-4 py-3 text-sm leading-7 shadow-sm ${
          isUser
            ? "bg-brand-600 text-white"
            : "border border-slate-200 bg-white text-slate-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>

      {isUser ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-700">
          <UserRound className="h-5 w-5" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  );
}
