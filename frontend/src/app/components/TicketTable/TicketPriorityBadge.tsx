import type { TicketPriority } from "@/types/ticket.types";

interface TicketPriorityBadgeProps {
  priority: TicketPriority;
}

const priorityConfig: Record<
  TicketPriority,
  { label: string; className: string }
> = {
  low: {
    label: "Baixa",
    className: "bg-slate-500/10 text-slate-400",
  },
  medium: {
    label: "Média",
    className: "bg-blue-500/10 text-blue-400",
  },
  high: {
    label: "Alta",
    className: "bg-orange-500/10 text-orange-400",
  },
  critical: {
    label: "Crítica",
    className: "bg-red-500/10 text-red-400",
  },
};

export function TicketPriorityBadge({
  priority,
}: TicketPriorityBadgeProps) {
  const config = priorityConfig[priority];

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}