import type { FormEvent } from "react";
import { Modal } from "./Modal";
import type { HistoryConversation } from "../types/history";

interface HistoryActionModalsProps {
  renameConversation: HistoryConversation | null;
  renameTitle: string;
  renameBusy?: boolean;
  deleteConversation: HistoryConversation | null;
  deleteBusy?: boolean;
  onRenameTitleChange: (title: string) => void;
  onRenameSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRenameClose: () => void;
  onDeleteConfirm: () => void;
  onDeleteClose: () => void;
}

export function HistoryActionModals({
  renameConversation,
  renameTitle,
  renameBusy = false,
  deleteConversation,
  deleteBusy = false,
  onRenameTitleChange,
  onRenameSubmit,
  onRenameClose,
  onDeleteConfirm,
  onDeleteClose,
}: HistoryActionModalsProps) {
  return (
    <>
      <Modal title="Rename Conversation" isOpen={Boolean(renameConversation)} onClose={onRenameClose}>
        <form onSubmit={onRenameSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="history-title" className="form-label">
              Title
            </label>
            <input
              id="history-title"
              value={renameTitle}
              onChange={(event) => onRenameTitleChange(event.target.value)}
              className="form-input"
              autoFocus
              maxLength={120}
            />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onRenameClose} className="btn-secondary" disabled={renameBusy}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={renameBusy || !renameTitle.trim()}>
              Save
            </button>
          </div>
        </form>
      </Modal>

      <Modal title="Delete Conversation" isOpen={Boolean(deleteConversation)} onClose={onDeleteClose}>
        <div className="space-y-4">
          <p className="text-sm leading-6 text-slate-600">
            Delete <span className="font-semibold text-slate-950">{deleteConversation?.title}</span>? This cannot be
            undone.
          </p>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onDeleteClose} className="btn-secondary" disabled={deleteBusy}>
              Cancel
            </button>
            <button
              type="button"
              onClick={onDeleteConfirm}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-100 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={deleteBusy}
            >
              Delete
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
