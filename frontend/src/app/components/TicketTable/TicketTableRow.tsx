import type { Ticket } from "@/types/ticket.types";

import { TicketStatusBadge } from "./TicketStatusBadge";
import { TicketPriorityBadge } from "./TicketPriorityBadge";

interface TicketTableRowProps {
  ticket: Ticket;
}

export function TicketTableRow({
  ticket,
}: TicketTableRowProps) {
  const createdAt = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(ticket.createdAt));

  return (
    <tr className="border-b border-slate-800 transition-colors hover:bg-slate-800/40">
      <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-slate-300">
        {ticket.id}
      </td>

      <td className="px-6 py-4">
        <p className="text-sm font-medium text-white">
          {ticket.title}
        </p>

        <p className="mt-1 text-xs text-slate-400">
          {ticket.description}
        </p>
      </td>

      <td className="px-6 py-4">
        <TicketStatusBadge status={ticket.status} />
      </td>

      <td className="px-6 py-4">
        <TicketPriorityBadge priority={ticket.priority} />
      </td>

      <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-400">
        {createdAt}
      </td>
    </tr>
  );
}