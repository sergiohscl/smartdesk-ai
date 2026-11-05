import {
  keepPreviousData,
  useQuery,
} from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

import type { TicketListParams } from "@/types/ticket.types";

export function useTickets({
  page = 1,
  pageSize = 10,
  status,
  priority,
  search,
}: TicketListParams = {}) {
  const normalizedSearch = search?.trim() || null;

  return useQuery({
    queryKey: [
      "tickets",
      "list",
      page,
      pageSize,
      status ?? null,
      priority ?? null,
      normalizedSearch,
    ],
    queryFn: () =>
      ticketService.getTickets({
        page,
        pageSize,
        status,
        priority,
        search: normalizedSearch ?? undefined,
      }),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}

export function useTicket(ticketId: string) {
  return useQuery({
    queryKey: ["tickets", "detail", ticketId],
    queryFn: () => ticketService.getById(ticketId),
    enabled: /^\d+$/.test(ticketId) && Number(ticketId) > 0,
    retry: false,
    staleTime: 30_000,
  });
}
