import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { AdminSidebar } from "../components/AdminSidebar";
import { UserMenu } from "../components/UserMenu";

export function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-cream">
      <AdminSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-cream-200 bg-white px-4 text-[#263238] shadow-sm">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-[#607D8B] hover:bg-brand-50 hover:text-brand-700 lg:hidden"
            aria-label="Open admin sidebar"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
          <div className="hidden text-sm font-semibold text-[#607D8B] lg:block">Admin Dashboard</div>
          <div className="[&_button]:text-[#607D8B] [&_button:hover]:bg-brand-50 [&_button:hover]:text-brand-700"><UserMenu /></div>
        </header>
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

