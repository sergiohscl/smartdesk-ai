import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

import type { TicketCreate } from "@/types/ticket.types";

export function useCreateTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TicketCreate) =>
      ticketService.createTicket(payload),

    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["tickets", "list"],
        }),

        queryClient.invalidateQueries({
          queryKey: ["tickets", "stats"],
        }),
      ]);
    },
  });
}
