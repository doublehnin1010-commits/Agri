import { HistoryActions } from "./HistoryActions";
import type { HistoryConversation } from "../types/history";

interface HistoryItemProps {
  conversation: HistoryConversation;
  active: boolean;
  onClick: (conversation: HistoryConversation) => void;
  onRename?: (conversation: HistoryConversation) => void;
  onDelete?: (conversation: HistoryConversation) => void;
  variant?: "light" | "dark";
}

export function HistoryItem({
  conversation,
  active,
  onClick,
  onRename,
  onDelete,
  variant = "light",
}: HistoryItemProps) {
  const itemClass =
    variant === "dark"
      ? active
        ? "bg-slate-800 text-white"
        : "text-slate-300 hover:bg-slate-800 hover:text-white"
      : active
        ? "bg-brand-50 text-brand-700"
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-950";

  return (
    <div
      className={`group flex min-h-10 items-stretch overflow-hidden rounded-lg text-sm font-medium transition ${itemClass}`}
    >
      <button
        type="button"
        onClick={() => onClick(conversation)}
        title={conversation.title}
        className="min-w-0 flex-1 truncate px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
      >
        {conversation.title}
      </button>
      <div className="flex shrink-0 items-center pr-2">
        <HistoryActions
          variant={variant}
          onRename={() => onRename?.(conversation)}
          onDelete={() => onDelete?.(conversation)}
        />
      </div>
    </div>
  );
}
