import { GraduationCap } from "lucide-react";

export function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
        <GraduationCap className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-slate-950">Myanmar Proverbs</p>
        <p className="truncate text-xs font-medium text-slate-500">AI Tutor</p>
      </div>
    </div>
  );
}
