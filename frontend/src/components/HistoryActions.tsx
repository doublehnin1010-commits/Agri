import { Edit3, Trash2 } from "lucide-react";

interface HistoryActionsProps {
  onRename: () => void;
  onDelete: () => void;
  variant?: "light" | "dark";
}

export function HistoryActions({ onRename, onDelete, variant = "light" }: HistoryActionsProps) {
  const renameClass =
    variant === "dark"
      ? "rounded-md p-1 text-slate-400 hover:bg-slate-700 hover:text-white"
      : "rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-800";
  const deleteClass =
    variant === "dark"
      ? "rounded-md p-1 text-slate-400 hover:bg-red-500/15 hover:text-red-300"
      : "rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600";

  return (
    <div className="flex items-center gap-1 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onRename();
        }}
        className={renameClass}
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
        className={deleteClass}
        aria-label="Delete conversation"
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
