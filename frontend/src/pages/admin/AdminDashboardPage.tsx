import { useQuery } from "@tanstack/react-query";
import { DatabaseZap, History, LibraryBig, MessageSquareText } from "lucide-react";
import { Link } from "react-router-dom";
import { StatCard } from "../../components/StatCard";
import { getHistory } from "../../services/chatService";
import { readLocalConversations } from "../../services/storage";

export function AdminDashboardPage() {
  const { data = [] } = useQuery({ queryKey: ["history", "admin-summary"], queryFn: () => getHistory(30) });
  const localCount = readLocalConversations().length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-950">Admin Dashboard</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Manage dataset imports, proverb records, and learning activity from one workspace.
          </p>
        </div>
        <Link to="/dashboard" className="btn-secondary">Open Tutor</Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Backend history" value={data.length} icon={History} />
        <StatCard label="Local sessions" value={localCount} icon={MessageSquareText} />
        <StatCard label="Dataset tools" value="DOCX" icon={DatabaseZap} />
        <StatCard label="Proverb CRUD" value="Ready" icon={LibraryBig} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Link to="/admin/import" className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-200 hover:shadow-soft">
          <DatabaseZap className="h-6 w-6 text-brand-700" aria-hidden="true" />
          <h2 className="mt-4 text-lg font-bold text-slate-950">Import Dataset</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">Upload matching Proverbs.docx and Meanings.docx files into the RAG collection.</p>
        </Link>
        <Link to="/admin/proverbs" className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-200 hover:shadow-soft">
          <LibraryBig className="h-6 w-6 text-brand-700" aria-hidden="true" />
          <h2 className="mt-4 text-lg font-bold text-slate-950">Proverbs Management</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">Create, search, paginate, and edit proverb records for the AI tutor.</p>
        </Link>
      </div>
    </div>
  );
}
