import { Menu } from "lucide-react";
import { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { UserMenu } from "../components/UserMenu";

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const handler = () => navigate("/login", { replace: true });
    window.addEventListener("auth:unauthorized", handler);
    return () => window.removeEventListener("auth:unauthorized", handler);
  }, [navigate]);

  return (
    <div className="flex h-screen overflow-hidden bg-cream">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-800 bg-slate-900 px-4 text-white sm:px-6">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-slate-200 hover:bg-slate-800 lg:hidden"
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
          <div className="hidden text-sm font-semibold text-slate-300 lg:block">Dashboard</div>
          <div className="[&_button]:text-slate-200 [&_button:hover]:bg-slate-800 [&_button:hover]:text-white"><UserMenu /></div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
