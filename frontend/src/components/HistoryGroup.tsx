import type { HistoryConversation } from "../types/history";
import { HistoryItem } from "./HistoryItem";

interface HistoryGroupProps {
  label: string;
  conversations: HistoryConversation[];
  activeId?: string;
  onSelect: (conversation: HistoryConversation) => void;
  onRename?: (conversation: HistoryConversation) => void;
  onDelete?: (conversation: HistoryConversation) => void;
}

export function HistoryGroup({ label, conversations, activeId, onSelect, onRename, onDelete }: HistoryGroupProps) {
  if (!conversations.length) return null;

  return (
    <section className="space-y-1">
      <h2 className="px-3 pt-4 text-xs font-bold uppercase tracking-wide text-slate-400">{label}</h2>
      <div className="space-y-0.5">
        {conversations.map((conversation) => (
          <HistoryItem
            key={conversation.id}
            conversation={conversation}
            active={conversation.id === activeId}
            onClick={onSelect}
            onRename={onRename}
            onDelete={onDelete}
          />
        ))}
      </div>
    </section>
  );
}
