
import { api } from "@/services/api";

import type {
  Ticket,
  TicketCreate,
  TicketListData,
  TicketListParams,
  TicketListResponse,
  TicketResponse,
  TicketStatsData,
  TicketStatsResponse,
} from "@/types/ticket.types";

function mapTicket(ticket: TicketResponse): Ticket {
  return {
    id: String(ticket.id),
    title: ticket.title,
    description: ticket.description,
    status: ticket.status,
    priority: ticket.priority,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at ?? ticket.created_at,
  };
}

export const ticketService = {
  async createTicket(payload: TicketCreate): Promise<Ticket> {
    const { data } = await api.post<TicketResponse>(
      "/tickets",
      payload,
    );

    return mapTicket(data);
  },

  async getById(ticketId: string): Promise<Ticket> {
    const { data } = await api.get<TicketResponse>(
      `/tickets/${ticketId}`,
    );

    return mapTicket(data);
  },

  async getStats(): Promise<TicketStatsData> {
    const { data } = await api.get<TicketStatsResponse>(
      "/tickets/stats",
    );

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
  }: TicketListParams = {}): Promise<TicketListData> {
    const { data } = await api.get<TicketListResponse>(
      "/tickets",
      {
        params: {
          page,
          page_size: pageSize,
        },
      },
    );

    return {
      items: data.items.map(mapTicket),
      total: data.total,
      page: data.page,
      pageSize: data.page_size,
      pages: data.pages,
    };
  },
};
