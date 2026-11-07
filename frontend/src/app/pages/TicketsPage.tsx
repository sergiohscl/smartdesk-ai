import { useEffect, useState } from "react";

import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";
import { TicketTable } from "@/app/components/TicketTable/TicketTable";

import { useTickets } from "@/hooks/useTickets";

import type {
  TicketPriority,
  TicketStatus,
} from "@/types/ticket.types";

const PAGE_SIZE = 10;

export function TicketsPage() {
  const [page, setPage] = useState(1);

  const [statusFilter, setStatusFilter] =
    useState<TicketStatus | "all">("all");

  const [priorityFilter, setPriorityFilter] =
    useState<TicketPriority | "all">("all");

  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 400);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [searchInput]);

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
    status: statusFilter === "all" ? undefined : statusFilter,
    priority: priorityFilter === "all" ? undefined : priorityFilter,
    search: debouncedSearch,
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


  const handleStatusFilterChange = (value: string) => {
    setStatusFilter(value as TicketStatus | "all");
    setPage(1);
  };

  const handlePriorityFilterChange = (value: string) => {
    setPriorityFilter(value as TicketPriority | "all");
    setPage(1);
  };

  const handleClearFilters = () => {
    setStatusFilter("all");
    setPriorityFilter("all");
    setSearchInput("");
    setDebouncedSearch("");
    setPage(1);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Chamados
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Gerencie os chamados de suporte do SmartDesk AI.
          </p>
        </div>


        <section
          aria-label="Filtros de chamados"
          className="rounded-xl border border-slate-800 bg-slate-900 p-5"
        >
          <div className="mb-4">
            <label
              htmlFor="tickets-search"
              className="mb-2 block text-sm font-medium text-slate-300"
            >
              Buscar chamado por título
            </label>
            <div className="flex gap-2">
              <input
                id="tickets-search"
                type="search"
                value={searchInput}
                onChange={(event) => {
                  setSearchInput(event.target.value);
                  setPage(1);
                }}
                placeholder="Digite o título do chamado..."
                maxLength={200}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-blue-500"
              />
              {searchInput !== "" && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchInput("");
                    setDebouncedSearch("");
                    setPage(1);
                  }}
                  className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800"
                >
                  Limpar
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="grid flex-1 gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="tickets-status-filter"
                  className="mb-2 block text-sm font-medium text-slate-300"
                >
                  Status
                </label>
                <select
                  id="tickets-status-filter"
                  value={statusFilter}
                  onChange={(event) =>
                    handleStatusFilterChange(event.target.value)
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white outline-none transition focus:border-blue-500"
                >
                  <option value="all">Todos os status</option>
                  <option value="open">Aberto</option>
                  <option value="in_progress">Em andamento</option>
                  <option value="resolved">Resolvido</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="tickets-priority-filter"
                  className="mb-2 block text-sm font-medium text-slate-300"
                >
                  Prioridade
                </label>
                <select
                  id="tickets-priority-filter"
                  value={priorityFilter}
                  onChange={(event) =>
                    handlePriorityFilterChange(event.target.value)
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white outline-none transition focus:border-blue-500"
                >
                  <option value="all">Todas as prioridades</option>
                  <option value="low">Baixa</option>
                  <option value="medium">Média</option>
                  <option value="high">Alta</option>
                  <option value="critical">Crítica</option>
                </select>
              </div>
            </div>
            <button
              type="button"
              onClick={handleClearFilters}
              disabled={
                statusFilter === "all" &&
                priorityFilter === "all" &&
                searchInput === "" &&
                debouncedSearch === ""
              }
              className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Limpar filtros
            </button>
          </div>
        </section>

        {isTicketsPending ? (
          <section
            role="status"
            className="rounded-xl border border-slate-800 bg-slate-900 px-6 py-12 text-center"
          >
            <p className="text-sm text-slate-400">
              Carregando chamados...
            </p>
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
            title="Todos os chamados"
            description="Consulte e gerencie os chamados registrados."
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
    </DashboardLayout>
  );
}
