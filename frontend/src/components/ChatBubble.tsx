import { Bot, UserRound } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types";

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700 shadow-sm">
          <Bot className="h-5 w-5" aria-hidden="true" />
        </div>
      ) : null}

      <div className={`text-sm leading-7 ${isUser ? "max-w-[min(680px,85%)] rounded-lg bg-brand-600 px-4 py-3 text-white shadow-sm" : "min-w-0 flex-1 rounded-lg border border-cream-200 bg-white px-5 py-5 text-[#263238] shadow-sm sm:px-6"}`}>
        {isUser ? (
          <div>
            <p className="whitespace-pre-wrap break-words text-[15px] leading-8">{message.content.replace(/^\[Image attached\]\n?/, "")}</p>
          </div>
        ) : (
          <ReactMarkdown
            components={{
              h1: ({ children }) => <h1 className="mb-4 text-xl font-bold leading-tight text-brand-700">{children}</h1>,
              h2: ({ children }) => <h2 className="mb-3 mt-6 text-lg font-bold leading-tight text-brand-700 first:mt-0">{children}</h2>,
              h3: ({ children }) => <h3 className="mb-2 mt-5 text-base font-bold leading-tight text-[#263238] first:mt-0">{children}</h3>,
              p: ({ children }) => <p className="mb-4 break-words leading-8 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="mb-4 list-disc space-y-2 pl-6 last:mb-0">{children}</ul>,
              ol: ({ children }) => <ol className="mb-4 list-decimal space-y-2 pl-6 last:mb-0">{children}</ol>,
              li: ({ children }) => <li className="break-words pl-1 leading-8">{children}</li>,
              strong: ({ children }) => <strong className="font-bold text-brand-700">{children}</strong>,
              blockquote: ({ children }) => <blockquote className="mb-4 border-l-4 border-brand-200 bg-brand-50 px-4 py-2 last:mb-0">{children}</blockquote>,
              code: ({ children, className }) => className ? (
                <code className="block overflow-x-auto rounded-lg bg-[#263238] p-3 text-sm leading-6 text-white">{children}</code>
              ) : (
                <code className="rounded bg-brand-50 px-1.5 py-0.5 text-sm font-semibold text-brand-700">{children}</code>
              ),
              a: ({ children, href }) => <a className="font-semibold text-brand-700 underline underline-offset-2 hover:text-brand-800" href={href}>{children}</a>,
              hr: () => <hr className="my-5 border-cream-200" />,
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>

      {isUser ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-[#263238]">
          <UserRound className="h-5 w-5" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  );
}



