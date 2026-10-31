import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";

import { TicketStats } from "@/app/components/TicketStats/TicketStats";
import { mockTicketStats } from "@/data/mockTicketStats";

export function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Visão geral
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Acompanhe e gerencie seus chamados de suporte.
          </p>
        </div>

        {/* Indicadores de chamados */}
        <TicketStats
          stats={mockTicketStats}
          isDemo
        />
      </div>
    </DashboardLayout>
  );
}
