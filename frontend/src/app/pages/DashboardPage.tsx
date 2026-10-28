import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";

export function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Visão geral
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Acompanhe e gerencie seus chamados de suporte.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="text-lg font-semibold">
            Gerenciamento de chamados
          </h3>

          <p className="mt-2 text-sm text-slate-400">
            Os indicadores e a listagem de chamados
            serão implementados nas próximas etapas.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}