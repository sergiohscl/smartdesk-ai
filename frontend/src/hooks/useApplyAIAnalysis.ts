import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { ticketService } from "@/services/ticketService";

import type { AIAnalysisApplyResponse } from "@/types/ai.types";

interface ApplyAIAnalysisVariables {
  ticketId: string;
  analysisId: number;
}

export function useApplyAIAnalysis() {
  const queryClient = useQueryClient();

  return useMutation<
    AIAnalysisApplyResponse,
    Error,
    ApplyAIAnalysisVariables
  >({
    mutationFn: ({ ticketId, analysisId }) =>
      ticketService.applyAIAnalysis(ticketId, analysisId),

    onSuccess: async (_result, variables) => {
      const ticketId = variables.ticketId;

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["tickets", "detail", ticketId],
        }),

        queryClient.invalidateQueries({
          queryKey: ["tickets", "list"],
        }),

        queryClient.invalidateQueries({
          queryKey: ["tickets", "stats"],
        }),

        queryClient.invalidateQueries({
          queryKey: ["tickets", "ai-history", ticketId],
        }),
      ]);
    },
  });
}
