import { Sparkles, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import axios from "axios";

import { useAnalyzeTicket } from "@/hooks/useAnalyzeTicket";
import { useApplyAIAnalysis } from "@/hooks/useApplyAIAnalysis";
import { useTicket } from "@/hooks/useTickets";
import { useAuth } from "@/app/providers/AuthProvider";
import { canManageTicket } from "@/utils/ticketPermissions";

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

export function TicketAIAnalysis({ ticketId }: TicketAIAnalysisProps) {
  const analysis = useAnalyzeTicket();
  const applyAIAnalysis = useApplyAIAnalysis();
  const { data: ticket } = useTicket(ticketId);

  const { user } = useAuth();

  // A assinatura exata será conferida com a página de detalhes.
  const canManage = Boolean(user && ticket && canManageTicket(user, ticket));

  const result =
    analysis.data?.ticket_id === Number(ticketId) ? analysis.data : null;

  const isPriorityApplied = Boolean(
    result &&
    applyAIAnalysis.isSuccess &&
    applyAIAnalysis.data?.analysis_id === result.analysis_id,
  );

  const canApplyPriority =
    Boolean(result && ticket && canManage) &&
    !isPriorityApplied &&
    !analysis.isPending &&
    !applyAIAnalysis.isPending;

  function handleAnalyze() {
    if (!canManage || analysis.isPending || applyAIAnalysis.isPending) {
      return;
    }

    applyAIAnalysis.reset();
    analysis.mutate(ticketId);
  }

  function handleApplyPriority() {
    if (!result || !ticket || !canApplyPriority) {
      return;
    }

    applyAIAnalysis.mutate({
      ticketId,
      analysisId: result.analysis_id,
    });
  }

  const isServiceUnavailable =
    axios.isAxiosError(analysis.error) &&
    analysis.error.response?.status === 503;

  const applyErrorStatus = axios.isAxiosError(applyAIAnalysis.error)
    ? applyAIAnalysis.error.response?.status
    : undefined;

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
          disabled={
            !canManage ||
            analysis.isPending ||
            applyAIAnalysis.isPending
          }
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {analysis.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}

          {analysis.isPending ? "Analisando..." : "Analisar com IA"}
        </button>
      </div>

      {ticket && !canManage && (
        <p className="mt-4 text-sm text-amber-400">
          Você pode visualizar este chamado, mas não possui permissão para
          realizar análises com IA.
        </p>
      )}

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
              <p className="text-xs text-slate-400">Prioridade sugerida</p>

              <p className="mt-2 font-semibold text-white">
                {priorityLabels[result.suggested_priority]}
              </p>
            </div>

            <div className="rounded-lg bg-slate-800/60 p-4">
              <p className="text-xs text-slate-400">Categoria sugerida</p>

              <p className="mt-2 font-semibold text-white">
                {categoryLabels[result.suggested_category]}
              </p>
            </div>
          </div>

          <div className="rounded-lg bg-slate-800/60 p-4">
            <p className="text-xs font-medium text-slate-400">Justificativa</p>

            <p className="mt-2 whitespace-pre-wrap wrap-break-word text-sm leading-6 text-slate-200">
              {result.reason}
            </p>
          </div>

          {canManage && !isPriorityApplied && (
            <button
              type="button"
              onClick={handleApplyPriority}
              disabled={!canApplyPriority}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {applyAIAnalysis.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <CheckCircle2 size={16} />
              )}

              {applyAIAnalysis.isPending
                ? "Aplicando prioridade..."
                : "Aplicar prioridade sugerida"}
            </button>
          )}

          {isPriorityApplied && (
            <div
              role="status"
              className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-400"
            >
              <CheckCircle2 size={18} className="shrink-0" />

              <p>Prioridade aplicada com sucesso.</p>
            </div>
          )}

          {applyAIAnalysis.isError && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400"
            >
              <AlertCircle size={18} className="shrink-0" />

              <p>
                {applyErrorStatus === 409
                  ? "Esta análise já foi aplicada anteriormente."
                  : applyErrorStatus === 403
                    ? "Você não possui permissão para aplicar esta análise."
                    : "Não foi possível aplicar a prioridade sugerida. Tente novamente."}
              </p>
            </div>
          )}

          <p className="text-xs text-slate-500">
            A análise da IA é apenas uma sugestão. A prioridade do chamado só
            será alterada mediante uma ação autorizada do usuário.
          </p>
        </div>
      )}
    </section>
  );
}
