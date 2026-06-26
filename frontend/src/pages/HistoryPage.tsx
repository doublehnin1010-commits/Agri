import { FormEvent, useEffect, useMemo, useState } from "react";
import { Loader2, MessagesSquare } from "lucide-react";
import toast from "react-hot-toast";
import { ChatMessages } from "../components/ChatMessages";
import { HistoryActionModals } from "../components/HistoryActionModals";
import { HistoryGroup } from "../components/HistoryGroup";
import { EmptyState } from "../components/EmptyState";
import { getApiErrorMessage } from "../api/client";
import { useHistory } from "../hooks/useHistory";
import { deleteHistory, renameHistory } from "../services/historyService";
import type { HistoryConversation } from "../types/history";
import { groupConversationsByDate, getConversationTitle } from "../utils/history";

export function HistoryPage() {
  const {
    conversationList,
    currentConversation,
    loading,
    error,
    loadHistory,
    selectConversation,
    renameConversation,
    removeConversation,
  } = useHistory();
  const [renamingConversation, setRenamingConversation] = useState<HistoryConversation | null>(null);
  const [deletingConversation, setDeletingConversation] = useState<HistoryConversation | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const groups = useMemo(() => groupConversationsByDate(conversationList), [conversationList]);
  const selectedConversation = useMemo(() => {
    if (currentConversation) {
      return conversationList.find((item) => item.id === currentConversation.id) || conversationList[0] || null;
    }
    return conversationList[0] || null;
  }, [conversationList, currentConversation]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

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

  useEffect(() => {
    if (!currentConversation && conversationList.length > 0) {
      selectConversation(conversationList[0]);
    }

    if (currentConversation && !conversationList.some((item) => item.id === currentConversation.id) && conversationList.length > 0) {
      selectConversation(conversationList[0]);
    }
  }, [conversationList, currentConversation, selectConversation]);

  return (
    <main className="flex h-full min-h-0 flex-1 flex-col bg-slate-50 overflow-hidden">
      <div className="border-b border-slate-200 bg-white px-4 py-4 sm:px-6">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold text-slate-950">Chat History</h1>
            <p className="mt-1 text-sm text-slate-500">
              Browse conversations grouped by time, then open any thread to review the full exchange.
            </p>
          </div>
          {loading ? (
            <div className="hidden items-center gap-2 text-sm font-semibold text-slate-500 sm:flex">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading
            </div>
          ) : null}
        </div>
      </div>

      <div className="grid h-full flex-1 gap-0 lg:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="flex h-full flex-col border-b border-slate-200 bg-white lg:border-b-0 lg:border-r">
          <div className="flex h-full flex-col overflow-hidden">
            <div className="border-b border-slate-200 px-4 py-4">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">History</p>
              <p className="mt-2 text-sm text-slate-500">
                Browse chat threads by date and open full conversations on the right.
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              {loading ? <HistoryLoadingSkeleton /> : null}

              {!loading && groups.length ? (
                <div className="space-y-2">
                  {groups.map((group) => (
                    <HistoryGroup
                      key={group.key}
                      label={group.label}
                      conversations={group.conversations}
                      activeId={selectedConversation?.id}
                      onSelect={selectConversation}
                      onRename={handleRename}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              ) : null}

              {!loading && !conversationList.length ? (
                <div className="p-2">
                  <EmptyState
                    icon={MessagesSquare}
                    title="No history yet"
                    description="When you send chat messages, they will show up here as grouped conversation threads."
                  />
                </div>
              ) : null}

              {error ? (
                <p className="mt-3 rounded-lg bg-red-50 p-3 text-xs font-medium leading-5 text-red-700">{error}</p>
              ) : null}
            </div>
          </div>
        </aside>

        <section className="flex h-full flex-1 overflow-hidden p-4 sm:p-6">
          {loading && !selectedConversation ? (
            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
              <HistoryThreadLoadingSkeleton />
            </div>
          ) : selectedConversation ? (
            <div className="flex h-full flex-col gap-4 overflow-hidden">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="truncate text-lg font-semibold text-slate-950">
                      {getConversationTitle(selectedConversation)}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {selectedConversation.messages.length} message
                      {selectedConversation.messages.length === 1 ? "" : "s"}
                    </p>
                  </div>
                </div>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="min-h-full">
                  <ChatMessages
                    messages={selectedConversation.messages}
                    showStarterSuggestions={false}
                    emptyStateTitle="This conversation is empty"
                    emptyStateDescription="There are no messages in this thread yet."
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
              <EmptyState
                icon={MessagesSquare}
                title="Select a conversation"
                description="Pick any thread on the left to open the complete chat history."
              />
            </div>
          )}
        </section>
      </div>

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
    </main>
  );
}

function HistoryLoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 px-3 text-xs font-semibold text-slate-400">
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        Loading history
      </div>
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="space-y-2 px-3 py-2">
          <div className="h-3 w-24 animate-pulse rounded bg-slate-100" />
          <div className="h-9 animate-pulse rounded-lg bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

function HistoryThreadLoadingSkeleton() {
  return (
    <div className="space-y-5">
      <div className="h-4 w-1/4 animate-pulse rounded bg-slate-100" />
      <div className="space-y-3">
        {[0, 1, 2, 3, 4].map((item) => (
          <div key={item} className="h-12 animate-pulse rounded-lg bg-slate-100" />
        ))}
      </div>
    </div>
  );
}
