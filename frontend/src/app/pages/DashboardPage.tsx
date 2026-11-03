
import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";
import { TicketStats } from "@/app/components/TicketStats/TicketStats";
import { TicketStatsSkeleton } from "@/app/components/TicketStats/TicketStatsSkeleton";
import { TicketStatsError } from "@/app/components/TicketStats/TicketStatsError";
import { TicketTable } from "@/app/components/TicketTable/TicketTable";

import { useTicketStats } from "@/hooks/useTicketStats";
import { useTickets } from "@/hooks/useTickets";

export function DashboardPage() {
  const {
    data: stats,
    isPending: isStatsPending,
    isError: isStatsError,
    isFetching: isStatsFetching,
    refetch: refetchStats,
  } = useTicketStats();

  const {
    data: ticketsData,
    isPending: isTicketsPending,
    isError: isTicketsError,
    isFetching: isTicketsFetching,
    refetch: refetchTickets,
  } = useTickets({
    page: 1,
    pageSize: 10,
  });

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

        {isStatsPending ? (
          <TicketStatsSkeleton />
        ) : isStatsError && !stats ? (
          <TicketStatsError
            onRetry={() => {
              void refetchStats();
            }}
            isRetrying={isStatsFetching}
          />
        ) : stats ? (
          <TicketStats stats={stats} />
        ) : null}

        <div className="space-y-4">
          {isTicketsPending ? (
            <section
              role="status"
              className="rounded-xl border border-slate-800 bg-slate-900 px-6 py-12 text-center"
            >
              <p className="text-sm text-slate-400">
                Carregando chamados...
              </p>
            </section>
          ) : isTicketsError && !ticketsData ? (
            <section
              role="alert"
              className="rounded-xl border border-red-900/50 bg-red-950/20 p-6"
            >
              <h3 className="font-semibold text-red-300">
                Não foi possível carregar os chamados
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                Verifique sua conexão e tente novamente.
              </p>

              <button
                type="button"
                onClick={() => {
                  void refetchTickets();
                }}
                disabled={isTicketsFetching}
                className="mt-4 rounded-lg bg-red-900/40 px-4 py-2 text-sm font-medium text-red-200 transition hover:bg-red-900/60 disabled:opacity-50"
              >
                {isTicketsFetching
                  ? "Tentando novamente..."
                  : "Tentar novamente"}
              </button>
            </section>
          ) : ticketsData ? (
            <TicketTable tickets={ticketsData.items} />
          ) : null}
        </div>
      </div>
    </DashboardLayout>
  );
}
