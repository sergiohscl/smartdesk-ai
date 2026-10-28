import { LogOut, Menu, UserRound } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";

import { useAuth } from "@/app/providers/AuthProvider";

interface DashboardHeaderProps {
  onOpenMenu: () => void;
}

export function DashboardHeader({
  onOpenMenu,
}: DashboardHeaderProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    logout();
    await navigate({ to: "/login", replace: true });
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900 px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="Abrir menu"
          onClick={onOpenMenu}
          className="text-slate-300 md:hidden"
        >
          <Menu size={24} />
        </button>

        <h1 className="text-lg font-semibold text-white">
          Dashboard
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-slate-300">
          <UserRound size={20} />

          <span className="hidden text-sm sm:inline">
            {user?.email ?? "Usuário"}
          </span>
        </div>

        <button
          type="button"
          onClick={() => void handleLogout()}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-400 transition hover:bg-red-500/10"
          aria-label="Sair da conta"
        >
          <LogOut size={18} />
          <span className="hidden sm:inline">Sair</span>
        </button>
      </div>
    </header>
  );
}