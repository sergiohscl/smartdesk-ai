interface ChatUsageIndicatorProps {
  used: number;
  limit: number;
}

export function ChatUsageIndicator({
  used,
  limit,
}: ChatUsageIndicatorProps) {
  const percentage =
    limit > 0
      ? Math.min(100, Math.max(0, (used / limit) * 100))
      : 0;

  return (
    <section
      aria-label="Utilização diária"
      className="space-y-3 border-t border-slate-800 p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-slate-400">
          Utilização diária
        </span>

        <span className="text-xs text-slate-300">
          {Math.round(percentage)}%
        </span>
      </div>

      <div
        role="progressbar"
        aria-label="Limite diário utilizado"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(percentage)}
        className="h-1.5 overflow-hidden rounded-full bg-slate-800"
      >
        <div
          style={{ width: `${percentage}%` }}
          className={`h-full rounded-full transition-all ${
            percentage >= 100
              ? "bg-red-500"
              : percentage >= 80
                ? "bg-amber-500"
                : "bg-blue-500"
          }`}
        />
      </div>

      <p className="text-xs text-slate-400">
        {used} de {limit} solicitações
      </p>

      {percentage >= 100 && (
        <p role="status" className="text-xs text-amber-400">
          Limite diário atingido.
        </p>
      )}
    </section>
  );
}
