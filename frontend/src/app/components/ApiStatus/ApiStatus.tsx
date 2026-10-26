import { useApiHealth } from "@/hooks/useApiHealth";

export function ApiStatus() {
  const { data, isPending, isError, isFetching } =
    useApiHealth();

  const isOnline = !isError && data?.status === "ok";

  if (isPending) {
    return (
      <span className="text-sm font-medium text-yellow-400">
        Verificando API...
      </span>
    );
  }

  return (
    <div
      className="flex items-center gap-2"
      role="status"
      aria-live="polite"
    >
      <span
        className={`size-3 rounded-full ${
          isOnline ? "bg-green-500" : "bg-red-500"
        }`}
      />

      <span
        className={`text-sm font-medium ${
          isOnline ? "text-green-400" : "text-red-400"
        }`}
      >
        {isOnline ? "API Online" : "API Offline"}
      </span>

      {isFetching && (
        <span className="text-xs text-gray-400">
          Atualizando...
        </span>
      )}
    </div>
  );
}