import { Sprout } from "lucide-react";

export function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-700 text-white shadow-sm">
        <Sprout className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-[#263238]">တို့ဦးကြီး</p>
        <p className="truncate text-xs font-medium text-[#607D8B]">စိုက်ပျိုးရေး AI အကူအညီပေးသူ</p>
      </div>
    </div>
  );
}

