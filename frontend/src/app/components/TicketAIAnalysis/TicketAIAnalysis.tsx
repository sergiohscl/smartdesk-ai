import { Sparkles, Loader2, AlertCircle } from "lucide-react";
import axios from "axios";

import { useAnalyzeTicket } from "@/hooks/useAnalyzeTicket";

import type { AITicketCategory } from "@/types/ai.types";
import type { TicketPriority } from "@/types/ticket.types";

interface TicketAIAnalysisProps {
  ticketId: string;
}

const categoryLabels: Record<AITicketCategory, string> = {
  hardware: "Hardware",
  software: "Software",
  network: "Rede",
  access: "Acesso",
  other: "Outros",
};

const priorityLabels: Record<TicketPriority, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

export function TicketAIAnalysis({
  ticketId,
}: TicketAIAnalysisProps) {
  const analysis = useAnalyzeTicket();

  const result =
    analysis.data?.ticket_id === Number(ticketId)
      ? analysis.data
      : null;

  function handleAnalyze() {
    if (analysis.isPending) return;

    analysis.mutate(ticketId);
  }

  const isServiceUnavailable =
    axios.isAxiosError(analysis.error) &&
    analysis.error.response?.status === 503;

  return (
    <section
      aria-labelledby="ticket-ai-title"
      className="rounded-xl border border-slate-800 bg-slate-900 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2
            id="ticket-ai-title"
            className="flex items-center gap-2 text-lg font-semibold text-white"
          >
            <Sparkles size={20} className="text-violet-400" />
            Análise inteligente
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Receba sugestões de prioridade e categoria com IA.
          </p>
        </div>

        <button
          type="button"
          onClick={handleAnalyze}
          disabled={analysis.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {analysis.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}

          {analysis.isPending
            ? "Analisando..."
            : "Analisar com IA"}
        </button>
      </div>

      {analysis.isPending && (
        <p role="status" className="mt-5 text-sm text-slate-400">
          A IA está analisando o chamado. Aguarde...
        </p>
      )}

      {analysis.isError && (
        <div
          role="alert"
          className="mt-5 flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400"
        >
          <AlertCircle size={18} className="shrink-0" />

          <p>
            {isServiceUnavailable
              ? "O serviço de IA está indisponível no momento. Tente novamente mais tarde."
              : "Não foi possível analisar o chamado. Tente novamente."}
          </p>
        </div>
      )}

      {analysis.isSuccess && result && (
        <div className="mt-6 space-y-4 border-t border-slate-800 pt-6">
          <h3 className="text-sm font-semibold text-slate-200">
            Resultado da análise
          </h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-800/60 p-4">
              <p className="text-xs text-slate-400">
                Prioridade sugerida
              </p>

              <p className="mt-2 font-semibold text-white">
                {priorityLabels[result.suggested_priority]}
              </p>
            </div>

            <div className="rounded-lg bg-slate-800/60 p-4">
              <p className="text-xs text-slate-400">
                Categoria sugerida
              </p>

              <p className="mt-2 font-semibold text-white">
                {categoryLabels[result.suggested_category]}
              </p>
            </div>
          </div>

          <div className="rounded-lg bg-slate-800/60 p-4">
            <p className="text-xs font-medium text-slate-400">
              Justificativa
            </p>

            <p className="mt-2 whitespace-pre-wrap wrap-break-word text-sm leading-6 text-slate-200">
              {result.reason}
            </p>
          </div>

          <p className="text-xs text-slate-500">
            Esta análise é apenas uma sugestão.
            Nenhuma informação do chamado foi alterada.
          </p>
        </div>
      )}
    </section>
  );
}
