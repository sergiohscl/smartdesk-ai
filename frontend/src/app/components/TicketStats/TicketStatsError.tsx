import { AlertCircle, RefreshCw } from "lucide-react";

interface TicketStatsErrorProps {
  onRetry: () => void;
  isRetrying?: boolean;
}

export function TicketStatsError({
  onRetry,
  isRetrying = false,
}: TicketStatsErrorProps) {
  return (
    <section
      role="alert"
      className="rounded-xl border border-red-900/50 bg-red-950/20 p-6"
    >
      <div className="flex items-start gap-3">
        <AlertCircle
          className="mt-0.5 h-5 w-5 shrink-0 text-red-400"
        />

        <div className="space-y-3">
          <div>
            <h3 className="font-semibold text-red-300">
              Não foi possível carregar os indicadores
            </h3>

            <p className="mt-1 text-sm text-slate-400">
              Verifique sua conexão ou tente novamente.
            </p>
          </div>

          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            className="inline-flex items-center gap-2 rounded-lg bg-red-900/40 px-4 py-2 text-sm font-medium text-red-200 transition hover:bg-red-900/60 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${
                isRetrying ? "animate-spin" : ""
              }`}
            />

            {isRetrying
              ? "Tentando novamente..."
              : "Tentar novamente"}
          </button>
        </div>
      </div>
    </section>
  );
}
