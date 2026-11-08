import type { TicketPriority } from "@/types/ticket.types";

export type AITicketCategory =
  | "hardware"
  | "software"
  | "network"
  | "access"
  | "other";

export interface AIAnalysisResponse {
  ticket_id: number;
  suggested_priority: TicketPriority;
  suggested_category: AITicketCategory;
  reason: string;
}
