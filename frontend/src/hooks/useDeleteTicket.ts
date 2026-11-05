import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

export function useDeleteTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId: string) =>
      ticketService.deleteTicket(ticketId),

    onSuccess: async (_data, ticketId) => {
      queryClient.removeQueries({
        queryKey: ["tickets", "detail", ticketId],
        exact: true,
      });

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
