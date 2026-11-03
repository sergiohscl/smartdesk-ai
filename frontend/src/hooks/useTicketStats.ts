import { useQuery } from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

export function useTicketStats() {
  return useQuery({
    queryKey: ["tickets", "stats"],
    queryFn: ticketService.getStats,
    staleTime: 30_000,
  });
}
