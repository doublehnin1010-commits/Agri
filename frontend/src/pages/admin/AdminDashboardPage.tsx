import { useQuery } from "@tanstack/react-query";
import { Database, FileText, MessageSquare, UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { listDocuments } from "../../services/documentService";

export function AdminDashboardPage() {
  const { data: documents = [], isLoading } = useQuery({ queryKey: ["documents", "admin-summary"], queryFn: listDocuments });
  const chunks = documents.reduce((sum, item) => sum + item.chunk_count, 0);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#263238]">Agriculture AI Admin</h1>
        <p className="mt-2 text-sm text-[#607D8B]">Manage the documents used by the agriculture assistant.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <OverviewItem label="Documents" value={isLoading ? "..." : documents.length.toLocaleString()} icon={FileText} />
        <OverviewItem label="Chunks" value={isLoading ? "..." : chunks.toLocaleString()} icon={Database} />
        <OverviewItem label="Vector database" value="ChromaDB" icon={Database} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ActionCard to="/admin/documents" icon={UploadCloud} title="Upload documents" description="Add PDF, DOCX, or TXT agriculture references and process them into vector chunks." action="Manage documents" />
        <ActionCard to="/dashboard" icon={MessageSquare} title="Test chat" description="Ask farming questions and verify retrieval-grounded Gemini answers." action="Open chat" />
      </div>
    </div>
  );
}

function OverviewItem({ label, value, icon: Icon }: { label: string; value: string; icon: typeof FileText }) {
  return (
    <div className="rounded-lg border border-cream-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-[#607D8B]">{label}</p>
        <Icon className="h-5 w-5 text-brand-600" aria-hidden="true" />
      </div>
      <p className="mt-3 text-2xl font-bold text-[#263238]">{value}</p>
    </div>
  );
}

function ActionCard({ to, icon: Icon, title, description, action }: { to: string; icon: typeof FileText; title: string; description: string; action: string }) {
  return (
    <Link to={to} className="rounded-lg border border-cream-200 bg-white p-5 shadow-sm transition hover:border-brand-300 hover:shadow-md">
      <Icon className="h-6 w-6 text-brand-600" aria-hidden="true" />
      <h2 className="mt-4 text-lg font-bold text-[#263238]">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-[#607D8B]">{description}</p>
      <p className="mt-4 text-sm font-bold text-brand-700">{action}</p>
    </Link>
  );
}

