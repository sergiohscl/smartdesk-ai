import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

import type {
  Ticket,
  TicketUpdate,
} from "@/types/ticket.types";

interface UpdateTicketVariables {
  ticketId: string;
  payload: TicketUpdate;
}

export function useUpdateTicket() {
  const queryClient = useQueryClient();

  return useMutation<Ticket, Error, UpdateTicketVariables>({
    mutationFn: ({ ticketId, payload }) =>
      ticketService.updateTicket(ticketId, payload),

    onSuccess: async (updatedTicket) => {
      queryClient.setQueryData(
        ["tickets", "detail", updatedTicket.id],
        updatedTicket,
      );

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
