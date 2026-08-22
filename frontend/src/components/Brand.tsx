export function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-lg bg-brand-700 shadow-sm">
        <img src="/doh-oo-gyi.png" alt="တို့ဦးကြီး logo" className="h-full w-full object-cover" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-[#263238]">တို့ဦးကြီး</p>
        <p className="truncate text-xs font-medium text-[#607D8B]">စိုက်ပျိုးရေးအကြံပေး AI</p>
      </div>
    </div>
  );
}

