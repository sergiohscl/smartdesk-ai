import type { TicketPriority } from "@/types/ticket.types";

export type AITicketCategory =
  | "hardware"
  | "software"
  | "network"
  | "access"
  | "other";

export interface AIAnalysisResponse {
  analysis_id: number;
  ticket_id: number;
  suggested_priority: TicketPriority;
  suggested_category: AITicketCategory;
  reason: string;
}

export interface AIAnalysisHistoryItem {
  id: number;
  ticket_id: number;
  suggested_priority: TicketPriority;
  suggested_category: AITicketCategory;
  reason: string;
  priority_at_analysis: TicketPriority;
  analyzed_by_id: number;
  created_at: string;
  applied_at: string | null;
  applied_by_id: number | null;
}

export interface AIAnalysisHistoryResponse {
  items: AIAnalysisHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AIAnalysisApplyResponse {
  analysis_id: number;
  ticket_id: number;
  previous_priority: TicketPriority;
  applied_priority: TicketPriority;
  applied_at: string;
  applied_by_id: number;
}
