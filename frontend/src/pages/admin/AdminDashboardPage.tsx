import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  ArrowRight,
  Brain,
  CheckCircle2,
  Database,
  DatabaseZap,
  FileText,
  LibraryBig,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  UserCog,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { StatCard } from "../../components/StatCard";
import { listProverbs } from "../../services/proverbService";

const importSteps = ["Import source files", "Generate metadata", "Create embeddings", "Update ChromaDB"];
const managementActions = ["Browse", "Search", "Filter", "Create", "Edit", "Delete"];

const futureFeatures: Array<{
  title: string;
  description: string;
  icon: LucideIcon;
}> = [
  {
    title: "Conversation Analytics",
    description: "View chatbot usage statistics and knowledge retrieval trends.",
    icon: BarChart3,
  },
  {
    title: "User Management",
    description: "Manage administrator accounts and access controls.",
    icon: UserCog,
  },
  {
    title: "System Configuration",
    description: "Manage LLM, embedding model, vector database, and platform settings.",
    icon: Settings2,
  },
];

export function AdminDashboardPage() {
  const { data: proverbs = [], isLoading } = useQuery({
    queryKey: ["proverbs", "admin-summary"],
    queryFn: listProverbs,
    retry: false,
  });

  return (
    <div className="space-y-7">
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="relative p-6 sm:p-8">
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-brand-600 via-sky-500 to-emerald-500" />
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-xs font-bold uppercase text-brand-700">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                RAG Administration
              </div>
              <h1 className="mt-4 text-3xl font-bold text-slate-950 sm:text-4xl">AI Knowledge Hub</h1>
              <p className="mt-3 text-sm leading-6 text-slate-500 sm:text-base">
                Manage your AI knowledge base, dataset ingestion, embeddings, and proverb records from a centralized workspace.
              </p>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
              <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              System Ready
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Knowledge Records"
          value={isLoading ? "..." : proverbs.length}
          icon={FileText}
          description="Proverb records available to the assistant."
          tone="brand"
        />
        <StatCard label="Language Model" value="Qwen3" icon={Brain} description="Current local LLM runtime." tone="violet" />
        <StatCard label="Embedding Model" value="BGE-M3" icon={Search} description="Semantic retrieval embeddings." tone="sky" />
        <StatCard label="Vector Database" value="ChromaDB" icon={Database} description="Knowledge index storage." tone="amber" />
        <StatCard label="System Status" value="Healthy" icon={ShieldCheck} description="Ready for knowledge operations." tone="emerald" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <FeatureCard
          to="/admin/import"
          icon={DatabaseZap}
          title="Knowledge Import"
          description="Import Proverbs.docx, Meanings.docx, and EnglishMeanings.docx, generate metadata and embeddings, then update the AI Knowledge Base with visible import progress."
          items={importSteps}
          action="Open import workspace"
        />
        <FeatureCard
          to="/admin/proverbs"
          icon={LibraryBig}
          title="Knowledge Management"
          description="Browse, search, filter, create, edit, and delete proverb knowledge records used by the AI assistant."
          items={managementActions}
          action="Manage knowledge records"
        />
      </div>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-slate-950">Platform Extensions</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">Planned administration modules for a fuller AI operations workspace.</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {futureFeatures.map((feature) => (
            <DisabledFeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </section>
    </div>
  );
}

interface FeatureCardProps {
  to: string;
  icon: LucideIcon;
  title: string;
  description: string;
  items: string[];
  action: string;
}

function FeatureCard({ to, icon: Icon, title, description, items, action }: FeatureCardProps) {
  return (
    <Link
      to={to}
      className="group flex min-h-80 flex-col rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-soft"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-50 text-brand-700 ring-1 ring-brand-100">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase text-slate-500 transition group-hover:bg-brand-50 group-hover:text-brand-700">
          Active
        </span>
      </div>
      <h2 className="mt-5 text-xl font-bold text-slate-950">{title}</h2>
      <p className="mt-3 text-sm leading-6 text-slate-500">{description}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
            {item}
          </span>
        ))}
      </div>
      <div className="mt-auto pt-6">
        <span className="inline-flex items-center gap-2 text-sm font-bold text-brand-700">
          {action}
          <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}

function DisabledFeatureCard({ title, description, icon: Icon }: { title: string; description: string; icon: LucideIcon }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-100/60 p-5 text-slate-400 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white text-slate-400 ring-1 ring-slate-200">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-bold uppercase text-slate-400">Coming Soon</span>
      </div>
      <h3 className="mt-4 text-base font-bold text-slate-600">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
    </div>
  );
}
