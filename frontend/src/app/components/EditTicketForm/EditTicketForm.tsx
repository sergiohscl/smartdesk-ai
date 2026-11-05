import { useState, type FormEvent } from "react";

import { useUpdateTicket } from "@/hooks/useUpdateTicket";

import type {
  Ticket,
  TicketPriority,
  TicketStatus,
  TicketUpdate,
} from "@/types/ticket.types";

interface EditTicketFormProps {
  ticket: Ticket;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function EditTicketForm({
  ticket,
  onSuccess,
  onCancel,
}: EditTicketFormProps) {
  const updateTicket = useUpdateTicket();

  const [title, setTitle] = useState(ticket.title);
  const [description, setDescription] = useState(
    ticket.description,
  );
  const [status, setStatus] = useState<TicketStatus>(
    ticket.status,
  );
  const [priority, setPriority] = useState<TicketPriority>(
    ticket.priority,
  );

  const normalizedTitle = title.trim();
  const normalizedDescription = description.trim();

  const hasChanges =
    normalizedTitle !== ticket.title ||
    normalizedDescription !== ticket.description ||
    status !== ticket.status ||
    priority !== ticket.priority;

  const isValid =
    normalizedTitle.length >= 3 &&
    normalizedTitle.length <= 200 &&
    normalizedDescription.length >= 5;

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      updateTicket.isPending ||
      !hasChanges ||
      !isValid
    ) {
      return;
    }

    const payload: TicketUpdate = {};

    if (normalizedTitle !== ticket.title) {
      payload.title = normalizedTitle;
    }

    if (normalizedDescription !== ticket.description) {
      payload.description = normalizedDescription;
    }

    if (status !== ticket.status) {
      payload.status = status;
    }

    if (priority !== ticket.priority) {
      payload.priority = priority;
    }

    try {
      await updateTicket.mutateAsync({
        ticketId: ticket.id,
        payload,
      });

      onSuccess?.();
    } catch {
      // O erro será exibido pelo estado da mutation.
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label
          htmlFor="edit-ticket-title"
          className="mb-2 block text-sm font-medium text-slate-200"
        >
          Título
        </label>

        <input
          id="edit-ticket-title"
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          minLength={3}
          maxLength={200}
          required
          disabled={updateTicket.isPending}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500 disabled:opacity-50"
        />
      </div>

      <div>
        <label
          htmlFor="edit-ticket-description"
          className="mb-2 block text-sm font-medium text-slate-200"
        >
          Descrição
        </label>

        <textarea
          id="edit-ticket-description"
          value={description}
          onChange={(event) =>
            setDescription(event.target.value)
          }
          minLength={5}
          required
          rows={5}
          disabled={updateTicket.isPending}
          className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500 disabled:opacity-50"
        />
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label
            htmlFor="edit-ticket-status"
            className="mb-2 block text-sm font-medium text-slate-200"
          >
            Status
          </label>

          <select
            id="edit-ticket-status"
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as TicketStatus)
            }
            disabled={updateTicket.isPending}
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500 disabled:opacity-50"
          >
            <option value="open">Aberto</option>
            <option value="in_progress">Em andamento</option>
            <option value="resolved">Resolvido</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="edit-ticket-priority"
            className="mb-2 block text-sm font-medium text-slate-200"
          >
            Prioridade
          </label>

          <select
            id="edit-ticket-priority"
            value={priority}
            onChange={(event) =>
              setPriority(
                event.target.value as TicketPriority,
              )
            }
            disabled={updateTicket.isPending}
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500 disabled:opacity-50"
          >
            <option value="low">Baixa</option>
            <option value="medium">Média</option>
            <option value="high">Alta</option>
            <option value="critical">Crítica</option>
          </select>
        </div>
      </div>

      {updateTicket.isError && (
        <div
          role="alert"
          className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300"
        >
          Não foi possível atualizar o chamado.
          Verifique os dados e tente novamente.
        </div>
      )}

      {updateTicket.isSuccess && (
        <div
          role="status"
          className="rounded-lg border border-green-800 bg-green-950/40 p-3 text-sm text-green-300"
        >
          Chamado atualizado com sucesso!
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={updateTicket.isPending}
            className="rounded-lg border border-slate-700 px-4 py-2 text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
          >
            Cancelar
          </button>
        )}

        <button
          type="submit"
          disabled={
            updateTicket.isPending ||
            !hasChanges ||
            !isValid
          }
          className="rounded-lg bg-blue-600 px-5 py-2 font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {updateTicket.isPending
            ? "Salvando alterações..."
            : "Salvar alterações"}
        </button>
      </div>
    </form>
  );
}
