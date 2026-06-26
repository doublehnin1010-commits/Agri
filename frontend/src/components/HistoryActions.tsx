import { Edit3, Trash2 } from "lucide-react";

interface HistoryActionsProps {
  onRename: () => void;
  onDelete: () => void;
}

export function HistoryActions({ onRename, onDelete }: HistoryActionsProps) {
  return (
    <div className="flex items-center gap-2 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100">
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onRename();
        }}
        className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-800"
        aria-label="Rename conversation"
      >
        <Edit3 className="h-4 w-4" aria-hidden="true" />
      </button>
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onDelete();
        }}
        className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
        aria-label="Delete conversation"
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
