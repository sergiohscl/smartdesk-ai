export function TicketStatsSkeleton() {
  return (
    <section
      aria-label="Carregando indicadores de chamados"
      role="status"
      className="w-full space-y-6"
    >
      <div className="space-y-2">
        <div className="h-7 w-64 animate-pulse rounded bg-slate-800" />
        <div className="h-4 w-72 max-w-full animate-pulse rounded bg-slate-800" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-36 animate-pulse rounded-xl border border-slate-800 bg-slate-900"
          />
        ))}
      </div>

      <span className="sr-only">
        Carregando indicadores...
      </span>
    </section>
  );
}
