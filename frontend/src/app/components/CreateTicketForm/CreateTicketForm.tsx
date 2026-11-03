import { useState, type FormEvent } from "react";

import { useCreateTicket } from "@/hooks/useCreateTicket";

import type {
  TicketCreate,
  TicketPriority,
} from "@/types/ticket.types";

interface CreateTicketFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function CreateTicketForm({
  onSuccess,
  onCancel,
}: CreateTicketFormProps) {
  const createTicket = useCreateTicket();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] =
    useState<TicketPriority>("medium");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (createTicket.isPending) {
      return;
    }

    const payload: TicketCreate = {
      title: title.trim(),
      description: description.trim(),
      priority,
    };

    if (!payload.title || !payload.description) {
      return;
    }

    try {
      await createTicket.mutateAsync(payload);

      setTitle("");
      setDescription("");
      setPriority("medium");

      onSuccess?.();
    } catch {
      // O erro será exibido pelo estado da mutation.
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5"
    >
      <div>
        <label
          htmlFor="ticket-title"
          className="mb-2 block text-sm font-medium text-slate-200"
        >
          Título
        </label>

        <input
          id="ticket-title"
          type="text"
          value={title}
          onChange={(event) =>
            setTitle(event.target.value)
          }
          maxLength={200}
          required
          disabled={createTicket.isPending}
          placeholder="Ex.: Computador não liga"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
        />
      </div>

      <div>
        <label
          htmlFor="ticket-description"
          className="mb-2 block text-sm font-medium text-slate-200"
        >
          Descrição
        </label>

        <textarea
          id="ticket-description"
          value={description}
          onChange={(event) =>
            setDescription(event.target.value)
          }
          required
          disabled={createTicket.isPending}
          rows={5}
          placeholder="Descreva o problema encontrado..."
          className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
        />
      </div>

      <div>
        <label
          htmlFor="ticket-priority"
          className="mb-2 block text-sm font-medium text-slate-200"
        >
          Prioridade
        </label>

        <select
          id="ticket-priority"
          value={priority}
          onChange={(event) =>
            setPriority(
              event.target.value as TicketPriority,
            )
          }
          disabled={createTicket.isPending}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
        >
          <option value="low">Baixa</option>
          <option value="medium">Média</option>
          <option value="high">Alta</option>
          <option value="critical">Crítica</option>
        </select>
      </div>

      {createTicket.isError && (
        <div
          role="alert"
          className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300"
        >
          Não foi possível criar o chamado.
          Verifique os dados e tente novamente.
        </div>
      )}

      {createTicket.isSuccess && (
        <div
          role="status"
          className="rounded-lg border border-green-800 bg-green-950/40 p-3 text-sm text-green-300"
        >
          Chamado criado com sucesso!
        </div>
      )}

      <div className="flex justify-end gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={createTicket.isPending}
            className="rounded-lg border border-slate-700 px-4 py-2 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            Cancelar
          </button>
        )}

        <button
          type="submit"
          disabled={createTicket.isPending}
          className="rounded-lg bg-blue-600 px-5 py-2 font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createTicket.isPending
            ? "Criando chamado..."
            : "Criar chamado"}
        </button>
      </div>
    </form>
  );
}
