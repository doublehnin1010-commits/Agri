import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  Database,
  DatabaseZap,
  LibraryBig,
  Search,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { listProverbs } from "../../services/proverbService";

export function AdminDashboardPage() {
  const { data: proverbs = [], isLoading } = useQuery({
    queryKey: ["proverbs", "admin-summary"],
    queryFn: listProverbs,
    retry: false,
  });

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-950">Dashboard</h1>
          <p className="mt-2 text-sm text-slate-500">Manage the knowledge used by your Myanmar Proverbs assistant.</p>
        </div>
        <div className="inline-flex w-fit items-center gap-2 text-sm font-semibold text-emerald-700">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          System ready
        </div>
      </header>

      <section aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="text-sm font-bold uppercase tracking-wide text-slate-500">Overview</h2>
        <div className="mt-3 grid overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm sm:grid-cols-2 xl:grid-cols-4">
          <OverviewItem label="Proverbs" value={isLoading ? "..." : proverbs.length.toLocaleString()} icon={LibraryBig} />
          <OverviewItem label="Language model" value="Qwen3" icon={Brain} />
          <OverviewItem label="Embeddings" value="BGE-M3" icon={Search} />
          <OverviewItem label="Vector database" value="ChromaDB" icon={Database} />
        </div>
      </section>

      <section aria-labelledby="actions-heading">
        <div>
          <h2 id="actions-heading" className="text-lg font-bold text-slate-950">Quick actions</h2>
          <p className="mt-1 text-sm text-slate-500">Choose where you want to work.</p>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <ActionCard
            to="/admin/import"
            icon={DatabaseZap}
            title="Import dataset"
            description="Upload proverb and meaning files, then create embeddings for ChromaDB."
            action="Open import"
          />
          <ActionCard
            to="/admin/proverbs"
            icon={LibraryBig}
            title="Manage proverbs"
            description="Search, review, create, edit, or remove proverb records."
            action="View proverbs"
          />
        </div>
      </section>
    </div>
  );
}

function OverviewItem({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
  return (
    <div className="flex items-center gap-3 border-b border-slate-200 p-5 last:border-b-0 sm:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 xl:[&:nth-child(2)]:border-r xl:last:border-r-0">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
        <p className="mt-1 truncate text-lg font-bold text-slate-950">{value}</p>
      </div>
    </div>
  );
}

interface ActionCardProps {
  to: string;
  icon: LucideIcon;
  title: string;
  description: string;
  action: string;
}

function ActionCard({ to, icon: Icon, title, description, action }: ActionCardProps) {
  return (
    <Link
      to={to}
      className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
    >
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-bold text-slate-950">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>
          <span className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-brand-700">
            {action}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </span>
        </div>
      </div>
    </Link>
  );
}
