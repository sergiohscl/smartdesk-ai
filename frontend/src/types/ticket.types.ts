export interface TicketStatsData {
  total: number;
  open: number;
  inProgress: number;
  resolved: number;
}

export type TicketStatus =
  | "open"
  | "in_progress"
  | "resolved";

export type TicketPriority =
  | "low"
  | "medium"
  | "high"
  | "critical";

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  createdAt: string;
  updatedAt: string;
}