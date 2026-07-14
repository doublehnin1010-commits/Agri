import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  description?: string;
  tone?: "brand" | "emerald" | "sky" | "violet" | "amber";
}

const toneClasses = {
  brand: "bg-brand-50 text-brand-700 ring-brand-100",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  sky: "bg-sky-50 text-sky-700 ring-sky-100",
  violet: "bg-violet-50 text-violet-700 ring-violet-100",
  amber: "bg-amber-50 text-amber-700 ring-amber-100",
};

export function StatCard({ label, value, icon: Icon, description, tone = "brand" }: StatCardProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
          {description ? <p className="mt-2 text-xs leading-5 text-slate-500">{description}</p> : null}
        </div>
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ring-1 ${toneClasses[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
