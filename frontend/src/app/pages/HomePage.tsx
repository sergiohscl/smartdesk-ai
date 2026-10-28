import { useNavigate } from "@tanstack/react-router";

import {
  BrainCircuit,
  Activity,
  LogOut,
  UserRound,
  Mail,
} from "lucide-react";

import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/app/components/ui/button";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/app/components/ui/card";

export function HomePage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();

    void navigate({
      to: "/login",
      replace: true,
    });
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#111827] p-6">
      <Card className="w-full max-w-md border-gray-700 bg-[#1F2937] text-white shadow-2xl">
        <CardHeader className="items-center text-center">
          <BrainCircuit className="mb-3 size-12 text-blue-400" />

          <CardTitle className="text-3xl font-bold text-white">
            SmartDesk AI
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-6">
          <p className="text-center text-gray-300">
            Sistema inteligente de gestão de chamados com IA.
          </p>

          <div className="space-y-4 rounded-lg border border-gray-600 bg-[#111827] p-4">
            <h2 className="text-sm font-semibold text-blue-400">
              Usuário autenticado
            </h2>

            <div className="flex items-center gap-3">
              <UserRound className="size-5 text-gray-400" />

              <div>
                <p className="text-xs text-gray-400">
                  Nome
                </p>

                <p className="font-medium text-white">
                  {user?.name}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Mail className="size-5 text-gray-400" />

              <div>
                <p className="text-xs text-gray-400">
                  E-mail
                </p>

                <p className="font-medium text-white">
                  {user?.email}
                </p>
              </div>
            </div>
          </div>

          <Button
            className="w-full bg-blue-600 text-white hover:bg-blue-700"
          >
            Começar
          </Button>

          <div className="rounded-lg border border-gray-600 bg-[#111827] p-4">
            <div className="flex items-center justify-center gap-2">
              <Activity className="size-4 text-blue-400" />

              <h2 className="text-sm font-semibold text-white">
                Status do Sistema
              </h2>
            </div>
          </div>

          <Button
            type="button"
            onClick={handleLogout}
            variant="outline"
            className="w-full border-red-500/40 bg-transparent text-red-400 hover:bg-red-500/10 hover:text-red-300"
          >
            <LogOut className="mr-2 size-4" />
            Sair da conta
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
