import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";

import { TicketStats } from "@/app/components/TicketStats/TicketStats";
import { TicketStatsSkeleton } from "@/app/components/TicketStats/TicketStatsSkeleton";
import { TicketStatsError } from "@/app/components/TicketStats/TicketStatsError";
import { TicketTable } from "@/app/components/TicketTable/TicketTable";

import { useTicketStats } from "@/hooks/useTicketStats";

import { mockTickets } from "@/data/mockTickets";

export function DashboardPage() {
  const {
    data: stats,
    isPending,
    isError,
    isFetching,
    refetch,
  } = useTicketStats();

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

        {/* Indicadores reais */}
        {isPending ? (
          <TicketStatsSkeleton />
        ) : isError && !stats ? (
          <TicketStatsError
            onRetry={() => {
              void refetch();
            }}
            isRetrying={isFetching}
          />
        ) : stats ? (
          <TicketStats stats={stats} />
        ) : null}

        {/* Listagem demonstrativa */}
        <TicketTable
          tickets={mockTickets}
          isDemo
        />
      </div>
    </DashboardLayout>
  );
}
