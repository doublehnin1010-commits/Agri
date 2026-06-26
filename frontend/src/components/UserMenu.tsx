import { ChevronDown, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex min-w-0 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
      >
        <UserRound className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="hidden max-w-36 truncate sm:block">{user?.email}</span>
        <ChevronDown className="h-4 w-4 shrink-0" aria-hidden="true" />
      </button>

      {open ? (
        <div className="absolute right-0 mt-2 w-64 rounded-lg border border-slate-200 bg-white p-2 shadow-soft">
          <div className="px-3 py-2">
            <p className="truncate text-sm font-bold text-slate-950">{user?.email}</p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              {user?.role ?? "user"}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Logout
          </button>
        </div>
      ) : null}
    </div>
  );
}
