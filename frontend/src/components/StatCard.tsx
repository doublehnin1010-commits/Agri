import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  description?: string;
  tone?: "brand" | "green" | "light";
}

const toneClasses = {
  brand: "bg-brand-50 text-brand-700 ring-brand-100",
  green: "bg-brand-600 text-white ring-brand-100",
  light: "bg-brand-50 text-brand-700 ring-brand-100",
};

export function StatCard({ label, value, icon: Icon, description, tone = "brand" }: StatCardProps) {
  return (
    <div className="rounded-lg border border-cream-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[#607D8B]">{label}</p>
          <p className="mt-2 text-2xl font-bold text-[#263238]">{value}</p>
          {description ? <p className="mt-2 text-xs leading-5 text-[#607D8B]">{description}</p> : null}
        </div>
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ring-1 ${toneClasses[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

