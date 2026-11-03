import { useState } from "react";

import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";
import { TicketStats } from "@/app/components/TicketStats/TicketStats";
import { TicketStatsSkeleton } from "@/app/components/TicketStats/TicketStatsSkeleton";
import { TicketStatsError } from "@/app/components/TicketStats/TicketStatsError";
import { TicketTable } from "@/app/components/TicketTable/TicketTable";
import { CreateTicketForm } from "@/app/components/CreateTicketForm/CreateTicketForm";

import { useTicketStats } from "@/hooks/useTicketStats";
import { useTickets } from "@/hooks/useTickets";

const PAGE_SIZE = 10;

export function DashboardPage() {
  const [page, setPage] = useState(1);
  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);

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
    isPlaceholderData,
    refetch: refetchTickets,
  } = useTickets({
    page,
    pageSize: PAGE_SIZE,
  });

  const handlePageChange = (nextPage: number) => {
    if (
      nextPage < 1 ||
      isTicketsFetching ||
      isPlaceholderData ||
      !ticketsData ||
      nextPage > ticketsData.pages
    ) {
      return;
    }

    setPage(nextPage);
  };

  const handleTicketCreated = () => {
    setIsCreateFormOpen(false);
    setPage(1);
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Visão geral</h2>

            <p className="mt-2 text-sm text-slate-400">
              Acompanhe e gerencie seus chamados de suporte.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setIsCreateFormOpen((previous) => !previous)}
            aria-expanded={isCreateFormOpen}
            aria-controls="create-ticket-panel"
            className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-500"
          >
            {isCreateFormOpen ? "Fechar formulário" : "+ Novo chamado"}
          </button>
        </div>

        {isCreateFormOpen && (
          <section
            id="create-ticket-panel"
            aria-label="Criar novo chamado"
            className="rounded-xl border border-slate-800 bg-slate-900 p-6"
          >
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white">
                Criar novo chamado
              </h3>

              <p className="mt-2 text-sm text-slate-400">
                Preencha as informações para registrar um novo chamado de
                suporte.
              </p>
            </div>

            <CreateTicketForm
              onSuccess={handleTicketCreated}
              onCancel={() => setIsCreateFormOpen(false)}
            />
          </section>
        )}

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
              <p className="text-sm text-slate-400">Carregando chamados...</p>
            </section>
          ) : isTicketsError ? (
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
            <TicketTable
              tickets={ticketsData.items}
              page={page}
              pageSize={PAGE_SIZE}
              total={ticketsData.total}
              totalPages={ticketsData.pages}
              onPageChange={handlePageChange}
              isFetching={isTicketsFetching}
              isPlaceholderData={isPlaceholderData}
            />
          ) : null}
        </div>
      </div>
    </DashboardLayout>
  );
}
