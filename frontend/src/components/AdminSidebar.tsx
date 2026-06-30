import { Book, DatabaseZap, LayoutDashboard, LibraryBig, PanelLeftClose } from "lucide-react";
import { NavLink } from "react-router-dom";
import { Brand } from "./Brand";

interface AdminSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const items = [
  { label: "Dashboard", to: "/admin", icon: LayoutDashboard },
  {label : "Open Chat" , to : "/dashboard" , icon : Book },
  { label: "Import Dataset", to: "/admin/import", icon: DatabaseZap },
  { label: "Proverbs Management", to: "/admin/proverbs", icon: LibraryBig },
];

export function AdminSidebar({ isOpen, onClose }: AdminSidebarProps) {
  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-950/40 transition lg:hidden ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
          <Brand />
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
            aria-label="Close admin sidebar"
          >
            <PanelLeftClose className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 p-3 ">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/admin"}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`
              }
            >
              <item.icon className="h-5 w-5" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}
