import type { Ticket } from "@/types/ticket.types";

import { TicketTableRow } from "./TicketTableRow";

interface TicketTableProps {
  tickets: Ticket[];
  isDemo?: boolean;
}

export function TicketTable({
  tickets,
  isDemo = false,
}: TicketTableProps) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-6 py-5">
        <div>
          <h3 className="text-lg font-semibold text-white">
            Chamados recentes
          </h3>

          <p className="mt-1 text-sm text-slate-400">
            Acompanhe os chamados de suporte.
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
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
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
    </section>
  );
}