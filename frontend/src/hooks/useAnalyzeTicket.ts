import { useMutation } from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

export function useAnalyzeTicket() {
  return useMutation({
    mutationFn: (ticketId: string) =>
      ticketService.analyzeTicket(ticketId),
    retry: false,
  });
}
