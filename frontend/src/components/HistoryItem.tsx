import { HistoryActions } from "./HistoryActions";
import type { HistoryConversation } from "../types/history";

interface HistoryItemProps {
  conversation: HistoryConversation;
  active: boolean;
  onClick: (conversation: HistoryConversation) => void;
  onRename?: (conversation: HistoryConversation) => void;
  onDelete?: (conversation: HistoryConversation) => void;
}

export function HistoryItem({
  conversation,
  active,
  onClick,
  onRename,
  onDelete,
}: HistoryItemProps) {
  return (
    <div
      className={`group flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition ${
        active
          ? "bg-brand-50 text-brand-700"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
      }`}
    >
      <button
        type="button"
        onClick={() => onClick(conversation)}
        title={conversation.title}
        className="min-w-0 truncate text-left"
      >
        {conversation.title}
      </button>
      <HistoryActions
        onRename={() => onRename?.(conversation)}
        onDelete={() => onDelete?.(conversation)}
      />
    </div>
  );
}
