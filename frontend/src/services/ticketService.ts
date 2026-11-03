import { api } from "@/services/api";

import type {
  TicketStatsData,
  TicketStatsResponse,
} from "@/types/ticket.types";

export const ticketService = {
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
};
