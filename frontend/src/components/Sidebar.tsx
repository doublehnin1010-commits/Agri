import { Loader2, MessageSquarePlus, PanelLeftClose, Shield } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { Brand } from "./Brand";
import { HistoryActionModals } from "./HistoryActionModals";
import { HistoryGroup } from "./HistoryGroup";
import { getApiErrorMessage } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import { useHistory } from "../hooks/useHistory";
import { deleteHistory, renameHistory } from "../services/historyService";
import type { HistoryConversation } from "../types/history";
import { groupConversationsByDate } from "../utils/history";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { user } = useAuth();
  const {
    conversationList,
    currentConversation,
    loading,
    error,
    loadHistory,
    selectConversation,
    startNewConversation,
    renameConversation,
    removeConversation,
  } = useHistory();
  const [renamingConversation, setRenamingConversation] = useState<HistoryConversation | null>(null);
  const [deletingConversation, setDeletingConversation] = useState<HistoryConversation | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const groups = useMemo(() => groupConversationsByDate(conversationList), [conversationList]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleNewChat = () => {
    startNewConversation();
    onClose();
  };

  const handleRename = (conversation: HistoryConversation) => {
    setRenamingConversation(conversation);
    setRenameTitle(conversation.title);
  };

  const handleRenameSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!renamingConversation) return;

    const trimmed = renameTitle.trim();
    if (!trimmed) {
      toast.error("Conversation title cannot be empty.");
      return;
    }

    setRenameBusy(true);
    try {
      await renameHistory(renamingConversation.id, trimmed);
      renameConversation(renamingConversation.id, trimmed);
      setRenamingConversation(null);
      toast.success("Conversation renamed.");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setRenameBusy(false);
    }
  };

  const handleDelete = (conversation: HistoryConversation) => {
    setDeletingConversation(conversation);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingConversation) return;

    setDeleteBusy(true);
    try {
      await deleteHistory(deletingConversation.id);
      removeConversation(deletingConversation.id);
      setDeletingConversation(null);
      toast.success("Conversation deleted.");
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-950/40 transition lg:hidden ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
          <Brand />
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
            aria-label="Close sidebar"
          >
            <PanelLeftClose className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="border-b border-slate-200 p-3">
          <button type="button" onClick={handleNewChat} className="btn-primary w-full justify-start">
            <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
            New Chat
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto p-3">
          {loading ? <HistorySkeleton /> : null}

          {!loading && !conversationList.length ? (
            <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-500">
              No chat history yet.
            </div>
          ) : null}

          {!loading && groups.length ? (
            <div className="space-y-2">
              {groups.map((group) => (
                <HistoryGroup
                  key={group.key}
                  label={group.label}
                  conversations={group.conversations}
                  activeId={currentConversation?.id}
                  onSelect={(conversation) => {
                    selectConversation(conversation);
                    onClose();
                  }}
                  onRename={handleRename}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          ) : null}

          {error ? (
            <p className="mt-3 rounded-lg bg-red-50 p-3 text-xs font-medium leading-5 text-red-700">{error}</p>
          ) : null}
        </nav>

        <div className="border-t border-slate-200 p-4">
          {user?.role === "admin" ? (
            <Link
              to="/admin"
              onClick={onClose}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
            >
              <Shield className="h-5 w-5" aria-hidden="true" />
              Admin
            </Link>
          ) : null}
        </div>
      </aside>

      <HistoryActionModals
        renameConversation={renamingConversation}
        renameTitle={renameTitle}
        renameBusy={renameBusy}
        deleteConversation={deletingConversation}
        deleteBusy={deleteBusy}
        onRenameTitleChange={setRenameTitle}
        onRenameSubmit={handleRenameSubmit}
        onRenameClose={() => setRenamingConversation(null)}
        onDeleteConfirm={handleDeleteConfirm}
        onDeleteClose={() => setDeletingConversation(null)}
      />
    </>
  );
}

function HistorySkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 px-3 text-xs font-semibold text-slate-400">
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        Loading history
      </div>
      {[0, 1, 2, 3, 4].map((item) => (
        <div key={item} className="h-9 animate-pulse rounded-lg bg-slate-100" />
      ))}
    </div>
  );
}
