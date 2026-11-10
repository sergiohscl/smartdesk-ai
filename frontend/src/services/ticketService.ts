import { api } from "@/services/api";
import type {
  AIAnalysisApplyResponse,
  AIAnalysisHistoryResponse,
  AIAnalysisResponse,
} from "@/types/ai.types";

import type {
  Ticket,
  TicketCreate,
  TicketListData,
  TicketListParams,
  TicketListResponse,
  TicketResponse,
  TicketStatsData,
  TicketStatsResponse,
  TicketUpdate,
} from "@/types/ticket.types";


function mapTicket(ticket: TicketResponse): Ticket {
  return {
    id: String(ticket.id),
    title: ticket.title,
    description: ticket.description,
    status: ticket.status,
    priority: ticket.priority,
    createdById: ticket.created_by_id,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at ?? ticket.created_at,
  };
}


export const ticketService = {
  async createTicket(payload: TicketCreate): Promise<Ticket> {
    const { data } = await api.post<TicketResponse>("/tickets", payload);

    return mapTicket(data);
  },

  async updateTicket(ticketId: string, payload: TicketUpdate): Promise<Ticket> {
    const { data } = await api.patch<TicketResponse>(
      `/tickets/${ticketId}`,
      payload,
    );

    return mapTicket(data);
  },

  async deleteTicket(ticketId: string): Promise<void> {
    await api.delete(`/tickets/${ticketId}`);
  },

  async getById(ticketId: string): Promise<Ticket> {
    const { data } = await api.get<TicketResponse>(`/tickets/${ticketId}`);

    return mapTicket(data);
  },

  async analyzeTicket(ticketId: string): Promise<AIAnalysisResponse> {
    const { data } = await api.post<AIAnalysisResponse>(
      `/tickets/${ticketId}/analyze`,
    );

    return data;
  },

  async getAIAnalysisHistory(
    ticketId: string,
    page = 1,
    pageSize = 10,
  ): Promise<AIAnalysisHistoryResponse> {
    const { data } = await api.get<AIAnalysisHistoryResponse>(
      `/tickets/${ticketId}/analyses`,
      {
        params: {
          page,
          page_size: pageSize,
        },
      },
    );

    return data;
  },

  async applyAIAnalysis(
    ticketId: string,
    analysisId: number,
  ): Promise<AIAnalysisApplyResponse> {
    const { data } = await api.post<AIAnalysisApplyResponse>(
      `/tickets/${ticketId}/analyses/${analysisId}/apply`,
    );

    return data;
  },

  async getStats(): Promise<TicketStatsData> {
    const { data } = await api.get<TicketStatsResponse>("/tickets/stats");

    return {
      total: data.total,
      open: data.open,
      inProgress: data.in_progress,
      resolved: data.resolved,
    };
  },

  async getTickets({
    page = 1,
    pageSize = 10,
    status,
    priority,
    search,
  }: TicketListParams = {}): Promise<TicketListData> {
    const normalizedSearch = search?.trim();

    const { data } = await api.get<TicketListResponse>("/tickets", {
      params: {
        page,
        page_size: pageSize,
        ...(status !== undefined && { status }),
        ...(priority !== undefined && { priority }),
        ...(normalizedSearch && { search: normalizedSearch }),
      },
    });

    return {
      items: data.items.map(mapTicket),
      total: data.total,
      page: data.page,
      pageSize: data.page_size,
      pages: data.pages,
    };
  },
}
