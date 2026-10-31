import {
  Ticket,
  Inbox,
  Clock3,
  CircleCheck,
} from "lucide-react";

import { StatCard } from "./StatCard";
import type { TicketStatsData } from "@/types/ticket.types";

interface TicketStatsProps {
  stats: TicketStatsData;
  isDemo?: boolean;
}

export function TicketStats({
  stats,
  isDemo = false,
}: TicketStatsProps) {
  const cards = [
    {
      title: "Total de chamados",
      value: stats.total,
      icon: Ticket,
      iconColor: "#60A5FA",
    },
    {
      title: "Chamados abertos",
      value: stats.open,
      icon: Inbox,
      iconColor: "#FBBF24",
    },
    {
      title: "Em andamento",
      value: stats.inProgress,
      icon: Clock3,
      iconColor: "#A78BFA",
    },
    {
      title: "Resolvidos",
      value: stats.resolved,
      icon: CircleCheck,
      iconColor: "#34D399",
    },
  ];

  return (
    <section
      aria-labelledby="ticket-stats-title"
      className="w-full space-y-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2
            id="ticket-stats-title"
            className="text-2xl font-semibold text-white"
          >
            Visão geral dos chamados
          </h2>

          <p className="mt-1 text-sm text-gray-400">
            Acompanhe os indicadores de atendimento
          </p>
        </div>

        {isDemo && (
          <span className="rounded-full border border-gray-600 bg-gray-800 px-3 py-1 text-xs font-medium text-gray-300">
            Dados demonstrativos
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <StatCard key={card.title} {...card} />
        ))}
      </div>
    </section>
  );
}
