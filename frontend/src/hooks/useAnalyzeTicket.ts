import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

export function useAnalyzeTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId: string) =>
      ticketService.analyzeTicket(ticketId),

    onSuccess: async (_result, ticketId) => {
      await queryClient.invalidateQueries({
        queryKey: ["tickets", "ai-history", ticketId],
      });
    },

    retry: false,
  });
}
