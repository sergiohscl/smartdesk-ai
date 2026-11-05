export interface TicketStatsData {
  total: number;
  open: number;
  inProgress: number;
  resolved: number;
}

export interface TicketStatsResponse {
  total: number;
  open: number;
  in_progress: number;
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

export interface TicketCreate {
  title: string;
  description: string;
  priority: TicketPriority;
}

export interface TicketUpdate {
  title?: string;
  description?: string;
  status?: TicketStatus;
  priority?: TicketPriority;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  createdAt: string;
  updatedAt: string;
}

export interface TicketResponse {
  id: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_by_id: number;
  created_at: string;
  updated_at: string;
}

export interface TicketListResponse {
  items: TicketResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TicketListData {
  items: Ticket[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface TicketListParams {
  page?: number;
  pageSize?: number;
  status?: TicketStatus;
  priority?: TicketPriority;
}
