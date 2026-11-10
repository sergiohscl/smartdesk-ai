
import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  History,
  Loader2,
} from "lucide-react";

import { useTicketAIHistory } from "@/hooks/useTicketAIHistory";
import { TicketPriorityBadge } from "@/app/components/TicketTable/TicketPriorityBadge";

import type {
  AIAnalysisHistoryItem,
  AITicketCategory,
} from "@/types/ai.types";

interface TicketAIHistoryProps {
  ticketId: string;
}

const PAGE_SIZE = 10;

const categoryLabels: Record<AITicketCategory, string> = {
  hardware: "Hardware",
  software: "Software",
  network: "Rede",
  access: "Acesso",
  other: "Outros",
};

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Data indisponível";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function HistoryItem({
  item,
}: {
  item: AIAnalysisHistoryItem;
}) {
  const wasApplied = item.applied_at !== null;

  return (
    <li className="rounded-lg border border-slate-800 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock3 size={16} aria-hidden="true" />
          <time dateTime={item.created_at}>
            {formatDate(item.created_at)}
          </time>
        </div>

        {wasApplied ? (
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
            <CheckCircle2 size={14} aria-hidden="true" />
            Prioridade aplicada
          </span>
        ) : (
          <span className="rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-300">
            Não aplicada
          </span>
        )}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs text-slate-400">
            Prioridade sugerida
          </p>
          <TicketPriorityBadge
            priority={item.suggested_priority}
          />
        </div>

        <div>
          <p className="mb-2 text-xs text-slate-400">
            Categoria sugerida
          </p>
          <p className="text-sm font-medium text-white">
            {categoryLabels[item.suggested_category]}
          </p>
        </div>

        <div>
          <p className="mb-2 text-xs text-slate-400">
            Prioridade no momento da análise
          </p>
          <TicketPriorityBadge
            priority={item.priority_at_analysis}
          />
        </div>

        <div>
          <p className="mb-2 text-xs text-slate-400">
            Identificador da análise
          </p>
          <p className="text-sm text-slate-200">
            #{item.id}
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-lg bg-slate-900/70 p-4">
        <p className="text-xs font-medium text-slate-400">
          Justificativa da IA
        </p>

        <p className="mt-2 whitespace-pre-wrap wrap-break-word text-sm leading-6 text-slate-200">
          {item.reason}
        </p>
      </div>

      <div className="mt-4 space-y-1 text-xs text-slate-500">
        <p>Analisado pelo usuário #{item.analyzed_by_id}</p>

        {wasApplied && item.applied_at && (
          <p>
            Aplicada em {formatDate(item.applied_at)}
            {item.applied_by_id !== null &&
              ` pelo usuário #${item.applied_by_id}`}
          </p>
        )}
      </div>
    </li>
  );
}

export function TicketAIHistory({
  ticketId,
}: TicketAIHistoryProps) {
  const [page, setPage] = useState(1);

  const history = useTicketAIHistory(
    ticketId,
    page,
    PAGE_SIZE,
  );

  const data = history.data;
  const totalPages = data?.pages ?? 0;

  const canGoPrevious = page > 1 && !history.isFetching;
  const canGoNext =
    Boolean(data && page < totalPages) &&
    !history.isFetching;

  return (
    <section
      aria-labelledby="ticket-ai-history-title"
      className="rounded-xl border border-slate-800 bg-slate-900 p-6"
    >
      <div className="flex items-center gap-3">
        <History
          size={20}
          className="text-violet-400"
          aria-hidden="true"
        />

        <div>
          <h2
            id="ticket-ai-history-title"
            className="text-lg font-semibold text-white"
          >
            Histórico de análises da IA
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Consulte as análises anteriores deste chamado.
          </p>
        </div>
      </div>

      {history.isPending && (
        <div
          role="status"
          className="mt-6 flex items-center gap-2 text-sm text-slate-400"
        >
          <Loader2
            size={18}
            className="animate-spin"
            aria-hidden="true"
          />
          Carregando histórico...
        </div>
      )}

      {history.isError && (
        <div
          role="alert"
          className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4"
        >
          <div className="flex items-center gap-2 text-sm text-red-400">
            <AlertCircle size={18} aria-hidden="true" />
            Não foi possível carregar o histórico.
          </div>

          <button
            type="button"
            onClick={() => void history.refetch()}
            className="mt-3 rounded-lg border border-red-500/30 px-3 py-2 text-sm text-red-300 transition hover:bg-red-500/10"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {history.isSuccess && data && (
        <div className="mt-6">
          {data.items.length === 0 ? (
            <p
              role="status"
              className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400"
            >
              {page === 1
                ? "Nenhuma análise registrada para este chamado."
                : "Nenhuma análise encontrada nesta página."}
            </p>
          ) : (
            <ol className="space-y-4">
              {data.items.map((item) => (
                <HistoryItem key={item.id} item={item} />
              ))}
            </ol>
          )}

          {data.total > 0 && (
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-800 pt-4">
              <p className="text-sm text-slate-400">
                {data.total}{" "}
                {data.total === 1 ? "análise" : "análises"}
                {" · "}Página {data.page} de {data.pages}
              </p>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setPage((current) =>
                      Math.max(1, current - 1),
                    )
                  }
                  disabled={!canGoPrevious}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft size={16} aria-hidden="true" />
                  Anterior
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setPage((current) =>
                      Math.min(totalPages, current + 1),
                    )
                  }
                  disabled={!canGoNext}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Próxima
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
