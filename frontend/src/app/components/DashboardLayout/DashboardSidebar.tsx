import { LayoutDashboard, Ticket, X } from "lucide-react";
import { Link } from "@tanstack/react-router";

interface DashboardSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DashboardSidebar({
  isOpen,
  onClose,
}: DashboardSidebarProps) {
  return (
    <>
      {isOpen && (
        <button
          type="button"
          aria-label="Fechar menu"
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64
          border-r border-slate-800 bg-slate-950
          transition-transform duration-200
          md:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-6">
          <span className="text-xl font-bold text-white">
            SmartDesk <span className="text-blue-500">AI</span>
          </span>

          <button
            type="button"
            aria-label="Fechar menu"
            onClick={onClose}
            className="text-slate-400 md:hidden"
          >
            <X size={22} />
          </button>
        </div>

        <nav aria-label="Navegação principal" className="space-y-2 p-4">
          <Link
            to="/"
            onClick={onClose}
            className="flex items-center gap-3 rounded-lg px-4 py-3 text-slate-300 transition hover:bg-slate-800 hover:text-white"
            activeProps={{
              className: "bg-blue-600 text-white",
            }}
          >
            <LayoutDashboard size={20} />
            Dashboard
          </Link>

          <div
            aria-disabled="true"
            className="flex cursor-not-allowed items-center gap-3 rounded-lg px-4 py-3 text-slate-500"
          >
            <Ticket size={20} />
            Chamados
            <span className="ml-auto text-xs">Em breve</span>
          </div>
        </nav>
      </aside>
    </>
  );
}