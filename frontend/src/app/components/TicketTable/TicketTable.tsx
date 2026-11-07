import type { Ticket } from "@/types/ticket.types";

import { TicketTableRow } from "./TicketTableRow";

interface TicketTableProps {
  tickets: Ticket[];
  isDemo?: boolean;
  title?: string;
  description?: string;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
  isPlaceholderData?: boolean;
}

export function TicketTable({
  tickets,
  isDemo = false,
  title = "Chamados recentes",
  description = "Acompanhe os chamados de suporte.",
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  isFetching = false,
  isPlaceholderData = false,
}: TicketTableProps) {
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  const isNavigationDisabled =
    isFetching || isPlaceholderData;

  const startItem =
    total === 0 ? 0 : (page - 1) * pageSize + 1;

  const endItem = Math.min(page * pageSize, total);

  return (
    <section
      aria-busy={isFetching}
      className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-6 py-5">
        <div>
          <h3 className="text-lg font-semibold text-white">
            {title}
          </h3>

          <p className="mt-1 text-sm text-slate-400">
            {description}
          </p>
        </div>

        {isDemo && (
          <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-400">
            Dados demonstrativos
          </span>
        )}
      </div>

      {tickets.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-sm text-slate-400">
            Nenhum chamado encontrado.
          </p>
        </div>
      ) : (
        <div
          className={`overflow-x-auto transition-opacity ${
            isFetching ? "opacity-60" : "opacity-100"
          }`}
        >
          <table className="w-full min-w-190 text-left">
            <thead className="bg-slate-800/50">
              <tr className="text-xs uppercase tracking-wider text-slate-400">
                <th scope="col" className="px-6 py-4">
                  ID
                </th>
                <th scope="col" className="px-6 py-4">
                  Chamado
                </th>
                <th scope="col" className="px-6 py-4">
                  Status
                </th>
                <th scope="col" className="px-6 py-4">
                  Prioridade
                </th>
                <th scope="col" className="px-6 py-4">
                  Criado em
                </th>
              </tr>
            </thead>

            <tbody>
              {tickets.map((ticket) => (
                <TicketTableRow
                  key={ticket.id}
                  ticket={ticket}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-col gap-4 border-t border-slate-800 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-400">
          Mostrando{" "}
          <span className="font-medium text-white">
            {startItem}–{endItem}
          </span>{" "}
          de{" "}
          <span className="font-medium text-white">
            {total}
          </span>{" "}
          chamados
        </p>

        <nav
          aria-label="Paginação de chamados"
          className="flex items-center gap-3"
        >
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={
              !canGoPrevious || isNavigationDisabled
            }
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Anterior
          </button>

          <span
            aria-live="polite"
            className="whitespace-nowrap text-sm text-slate-400"
          >
            Página{" "}
            <span className="font-semibold text-white">
              {page}
            </span>{" "}
            de {Math.max(totalPages, 1)}
          </span>

          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={
              !canGoNext || isNavigationDisabled
            }
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Próxima
          </button>
        </nav>
      </div>
    </section>
  );
}
