import { useQuery } from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

import type { TicketListParams } from "@/types/ticket.types";

export function useTickets({
  page = 1,
  pageSize = 10,
}: TicketListParams = {}) {
  return useQuery({
    queryKey: ["tickets", "list", page, pageSize],
    queryFn: () =>
      ticketService.getTickets({
        page,
        pageSize,
      }),
    staleTime: 30_000,
  });
}
