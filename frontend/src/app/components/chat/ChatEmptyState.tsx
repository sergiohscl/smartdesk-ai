import {
  Bot,
  Database,
  Network,
  Terminal,
  Ticket,
} from "lucide-react";

interface ChatEmptyStateProps {
  onSuggestion: (message: string) => void;
  disabled?: boolean;
}

const suggestions = [
  {
    icon: Database,
    title: "Banco de dados",
    description: "Diagnóstico e consultas SQL",
    message: "Como diagnosticar problemas de conexão com PostgreSQL?",
  },
  {
    icon: Network,
    title: "Redes e conectividade",
    description: "Resolva problemas de conexão",
    message: "Como diagnosticar problemas de conectividade de rede?",
  },
  {
    icon: Terminal,
    title: "Desenvolvimento",
    description: "Auxílio com código e ferramentas",
    message: "Como investigar erros em uma aplicação backend?",
  },
  {
    icon: Ticket,
    title: "Suporte técnico",
    description: "Orientação sobre chamados",
    message: "Como elaborar um chamado de suporte técnico completo?",
  },
];

export function ChatEmptyState({
  onSuggestion,
  disabled = false,
}: ChatEmptyStateProps) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center px-4 py-4">
      <div className="mb-3 rounded-xl border border-blue-500/20 bg-blue-500/10 p-3">
        <Bot size={28} className="text-blue-400" />
      </div>

      <h2 className="text-center text-xl font-semibold text-white">
        Como posso ajudar?
      </h2>

      <p className="mt-2 text-center text-xs text-slate-400">
        Seu assistente inteligente de suporte técnico e tecnologia.
      </p>

      <div className="mt-4 grid w-full gap-2 sm:grid-cols-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.title}
            type="button"
            disabled={disabled}
            onClick={() => onSuggestion(suggestion.message)}
            className="rounded-xl border border-slate-800 bg-slate-900 p-3 text-left transition hover:border-blue-500/50 hover:bg-slate-800 disabled:opacity-50"
          >
            <suggestion.icon
              size={18}
              className="mb-1 text-blue-400"
            />

            <span className="block text-sm font-medium text-white">
              {suggestion.title}
            </span>

            <span className="mt-1 block text-xs text-slate-400">
              {suggestion.description}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
