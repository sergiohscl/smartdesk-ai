import { useQuery } from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

export function useTicketAIHistory(
  ticketId: string,
  page = 1,
  pageSize = 10,
) {
  const isValidTicketId =
    /^\d+$/.test(ticketId) &&
    Number.isSafeInteger(Number(ticketId)) &&
    Number(ticketId) > 0;

  return useQuery({
    queryKey: [
      "tickets",
      "ai-history",
      ticketId,
      page,
      pageSize,
    ],
    queryFn: () =>
      ticketService.getAIAnalysisHistory(
        ticketId,
        page,
        pageSize,
      ),
    enabled:
      isValidTicketId &&
      Number.isInteger(page) &&
      page >= 1 &&
      Number.isInteger(pageSize) &&
      pageSize >= 1 &&
      pageSize <= 100,
    retry: false,
    staleTime: 30_000,
  });
}
