import { useState } from "react";

import {
  Bot,
  Check,
  Copy,
  RefreshCw,
  UserRound,
} from "lucide-react";

import { ChatMarkdown } from "./ChatMarkdown";

import type {
  ChatMessageRole,
  ChatMessageStatus,
} from "@/types/chat.types";

interface ChatMessageProps {
  role: ChatMessageRole;
  content: string;
  status: ChatMessageStatus;
  onRegenerate?: () => void;
}

const statusLabels: Record<ChatMessageStatus, string> = {
  pending: "Gerando resposta...",
  completed: "",
  failed: "Não foi possível concluir a resposta.",
  cancelled: "Geração cancelada.",
  truncated: "Resposta interrompida pelo limite de geração.",
};

export function ChatMessage({
  role,
  content,
  status,
  onRegenerate,
}: ChatMessageProps) {
  const [copyStatus, setCopyStatus] = useState<
    "idle" | "copied" | "failed"
  >("idle");

  const isAssistant = role === "assistant";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  };

  return (
    <article
      className={`flex items-start gap-3 ${
        isAssistant ? "" : "flex-row-reverse"
      }`}
    >
      <div
        className={`shrink-0 rounded-xl p-2.5 ${
          isAssistant
            ? "bg-blue-500/10 text-blue-400"
            : "bg-slate-800 text-slate-300"
        }`}
      >
        {isAssistant ? <Bot size={20} /> : <UserRound size={20} />}
      </div>

      <div
        className={`min-w-0 max-w-[85%] rounded-2xl px-4 py-3 ${
          isAssistant
            ? "flex-1 bg-slate-900/60"
            : "bg-blue-600/15"
        }`}
      >
        <p className="mb-2 text-xs font-semibold text-slate-400">
          {isAssistant ? "SmartDesk Assistant" : "Você"}
        </p>

        {isAssistant ? (
          <ChatMarkdown content={content} />
        ) : (
          <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-200">
            {content}
          </p>
        )}

        {status !== "completed" && (
          <p
            role="status"
            className={`mt-3 text-xs ${
              status === "failed"
                ? "text-red-400"
                : "text-amber-400"
            }`}
          >
            {statusLabels[status]}
          </p>
        )}

        {isAssistant && status !== "pending" && (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {content && (
              <button
                type="button"
                aria-label="Copiar resposta"
                title="Copiar resposta"
                onClick={() => void handleCopy()}
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                {copyStatus === "copied" ? (
                  <Check size={16} />
                ) : (
                  <Copy size={16} />
                )}
              </button>
            )}

            {onRegenerate && (
              <button
                type="button"
                aria-label="Regenerar resposta"
                title="Regenerar resposta"
                onClick={onRegenerate}
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <RefreshCw size={16} />
              </button>
            )}

            {copyStatus === "failed" && (
              <span role="alert" className="text-xs text-red-400">
                Não foi possível copiar.
              </span>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
