import { MessageSquare, Plus } from "lucide-react";

import { ChatUsageIndicator } from "./ChatUsageIndicator";

import type {
  ChatConversation,
  ChatUsage,
} from "@/types/chat.types";

interface ChatSidebarProps {
  conversations: ChatConversation[];
  selectedId: number;
  usage?: ChatUsage;
  onSelect: (id: number) => void;
  onCreate: () => void;
  onPageChange: (page: number) => void;
  page: number;
  pages: number;
  disabled: boolean;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

export function ChatSidebar({
  conversations,
  selectedId,
  usage,
  onSelect,
  onCreate,
  onPageChange,
  page,
  pages,
  disabled,
  isLoading,
  isError,
  onRetry,
}: ChatSidebarProps) {
  return (
    <aside className="flex min-w-0 flex-col rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 p-4">
        <button
          type="button"
          onClick={onCreate}
          disabled={disabled}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          <Plus size={18} />
          Nova conversa
        </button>
      </div>

      <div className="min-h-0 max-h-36 flex-1 space-y-1 overflow-y-auto p-2 xl:max-h-none">
        <h3 className="px-2 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Conversas
        </h3>

        {isLoading && (
          <p role="status" className="p-2 text-sm text-slate-400">
            Carregando conversas...
          </p>
        )}

        {isError && (
          <button
            type="button"
            onClick={onRetry}
            className="p-2 text-sm text-red-300"
          >
            Falha ao carregar. Tentar novamente.
          </button>
        )}

        {!isLoading && !isError && conversations.length === 0 && (
          <p className="p-2 text-sm text-slate-500">
            Nenhuma conversa registrada.
          </p>
        )}

        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            title={conversation.title}
            aria-pressed={selectedId === conversation.id}
            disabled={disabled}
            onClick={() => onSelect(conversation.id)}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm transition disabled:opacity-50 ${
              selectedId === conversation.id
                ? "bg-blue-500/15 text-blue-300"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <MessageSquare size={17} className="shrink-0" />

            <span className="min-w-0 flex-1 truncate">
              {conversation.title}
            </span>

            {conversation.generation_status === "generating" && (
              <span
                aria-label="Geração em andamento"
                className="h-2 w-2 shrink-0 rounded-full bg-blue-400"
              />
            )}
          </button>
        ))}
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-between gap-2 border-t border-slate-800 p-3 text-xs text-slate-400">
          <button
            type="button"
            disabled={disabled || page <= 1}
            onClick={() => onPageChange(page - 1)}
            className="disabled:opacity-40"
          >
            Anterior
          </button>

          <span>{page}/{pages}</span>

          <button
            type="button"
            disabled={disabled || page >= pages}
            onClick={() => onPageChange(page + 1)}
            className="disabled:opacity-40"
          >
            Próxima
          </button>
        </div>
      )}

      {usage && (
        <ChatUsageIndicator
          used={usage.used}
          limit={usage.daily_limit}
        />
      )}
    </aside>
  );
}
