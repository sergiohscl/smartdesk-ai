import type { TicketStatus } from "@/types/ticket.types";

interface TicketStatusBadgeProps {
  status: TicketStatus;
}

const statusConfig: Record<
  TicketStatus,
  { label: string; className: string }
> = {
  open: {
    label: "Aberto",
    className: "bg-blue-500/10 text-blue-400",
  },
  in_progress: {
    label: "Em andamento",
    className: "bg-yellow-500/10 text-yellow-400",
  },
  resolved: {
    label: "Resolvido",
    className: "bg-green-500/10 text-green-400",
  },
};

export function TicketStatusBadge({
  status,
}: TicketStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}