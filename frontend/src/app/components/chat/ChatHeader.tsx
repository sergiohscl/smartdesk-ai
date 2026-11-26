import { Bot, Home, Pencil, Trash2 } from "lucide-react";

interface ChatHeaderProps {
  title: string;
  disabled: boolean;
  hasConversation: boolean;
  onBackToHelp: () => void;
  backDisabled: boolean;
  onRename: () => void;
  onDelete: () => void;
}

export function ChatHeader({
  title,
  disabled,
  hasConversation,
  onBackToHelp,
  backDisabled,
  onRename,
  onDelete,
}: ChatHeaderProps) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-800 p-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="shrink-0 rounded-xl bg-blue-500/10 p-3">
          <Bot size={24} className="text-blue-400" />
        </div>

        <div className="min-w-0">
          <h2 className="truncate font-semibold text-white">
            {title}
          </h2>

          <p className="text-xs text-slate-400">
            SmartDesk Assistant
          </p>
        </div>
      </div>

      {hasConversation && (
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            aria-label="Voltar para ajuda"
            title="Voltar para ajuda"
            onClick={onBackToHelp}
            disabled={backDisabled}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-blue-400 disabled:opacity-40"
          >
            <Home size={18} />
          </button>

          <button
            type="button"
            aria-label="Renomear conversa"
            title="Renomear conversa"
            onClick={onRename}
            disabled={disabled}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-40"
          >
            <Pencil size={18} />
          </button>

          <button
            type="button"
            aria-label="Excluir conversa"
            title="Excluir conversa"
            onClick={onDelete}
            disabled={disabled}
            className="rounded-lg p-2 text-slate-400 hover:bg-red-950/40 hover:text-red-400 disabled:opacity-40"
          >
            <Trash2 size={18} />
          </button>
        </div>
      )}
    </header>
  );
}
