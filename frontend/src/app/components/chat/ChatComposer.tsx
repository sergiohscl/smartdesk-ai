import { ArrowUp, Square } from "lucide-react";

interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onCancel: () => void;
  isGenerating: boolean;
  disabled?: boolean;
  canCancel?: boolean;
}

const MAX_MESSAGE_LENGTH = 8000;

export function ChatComposer({
  value,
  onChange,
  onSend,
  onCancel,
  isGenerating,
  disabled = false,
  canCancel = true,
}: ChatComposerProps) {
  const canSend =
    !disabled &&
    !isGenerating &&
    value.trim().length > 0 &&
    value.length <= MAX_MESSAGE_LENGTH;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <form
        onSubmit={(event) => {
          event.preventDefault();

          if (canSend) {
            onSend();
          }
        }}
        className="rounded-2xl border border-slate-700 bg-slate-900 p-2 focus-within:border-blue-500"
      >
        <textarea
          aria-label="Mensagem para o assistente"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          maxLength={MAX_MESSAGE_LENGTH}
          disabled={disabled || isGenerating}
          placeholder="Digite sua mensagem..."
          rows={2}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();

              if (canSend) {
                onSend();
              }
            }
          }}
          className="w-full max-h-32 resize-y bg-transparent px-2 py-2 text-sm text-white outline-none placeholder:text-slate-500"
        />

        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 px-2 text-xs text-slate-400">
            <span>Qwen 2.5 · 7B</span>
            <span>{value.length}/{MAX_MESSAGE_LENGTH}</span>
          </div>

          {isGenerating ? (
            <button
              type="button"
              aria-label="Cancelar geração"
              title="Cancelar geração"
              onClick={onCancel}
              disabled={!canCancel}
              className="rounded-xl bg-slate-700 p-3 text-white hover:bg-slate-600 disabled:opacity-40"
            >
              <Square size={18} />
            </button>
          ) : (
            <button
              type="submit"
              aria-label="Enviar mensagem"
              title="Enviar mensagem"
              disabled={!canSend}
              className="rounded-xl bg-blue-600 p-3 text-white hover:bg-blue-500 disabled:opacity-40"
            >
              <ArrowUp size={18} />
            </button>
          )}
        </div>
      </form>

      <p className="mt-2 text-center text-xs text-slate-500">
        A IA pode cometer erros. Verifique informações importantes.
      </p>
    </div>
  );
}
