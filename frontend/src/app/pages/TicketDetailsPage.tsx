import { useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, CalendarDays, Hash, Pencil } from "lucide-react";
import axios from "axios";

import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";
import { EditTicketForm } from "@/app/components/EditTicketForm/EditTicketForm";
import { TicketPriorityBadge } from "@/app/components/TicketTable/TicketPriorityBadge";
import { TicketStatusBadge } from "@/app/components/TicketTable/TicketStatusBadge";
import { useTicket } from "@/hooks/useTickets";

function formatDate(date: string) {
  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Data indisponível";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsedDate);
}

export function TicketDetailsPage() {
  const [editingTicketId, setEditingTicketId] = useState<string | null>(null);

  const { ticketId } = useParams({
    from: "/tickets/$ticketId",
  });

  const isValidTicketId =
    /^\d+$/.test(ticketId) &&
    Number.isSafeInteger(Number(ticketId)) &&
    Number(ticketId) > 0;

  const {
    data: ticket,
    isPending,
    isError,
    error,
  } = useTicket(isValidTicketId ? ticketId : "");

  const isNotFound =
    axios.isAxiosError(error) && error.response?.status === 404;

  const isEditing = Boolean(ticket && editingTicketId === ticket.id);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
        >
          <ArrowLeft size={16} />
          Voltar ao dashboard
        </Link>

        {!isValidTicketId ? (
          <div
            role="alert"
            className="rounded-xl border border-slate-800 bg-slate-900 p-6"
          >
            <p className="text-red-400">ID do chamado inválido.</p>
          </div>
        ) : isPending ? (
          <div
            role="status"
            className="rounded-xl border border-slate-800 bg-slate-900 p-6"
          >
            <p className="text-slate-400">Carregando detalhes do chamado...</p>
          </div>
        ) : isError ? (
          <div
            role="alert"
            className="rounded-xl border border-slate-800 bg-slate-900 p-6"
          >
            <p className="text-red-400">
              {isNotFound
                ? "Chamado não encontrado."
                : "Não foi possível carregar os detalhes do chamado."}
            </p>
          </div>
        ) : ticket ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-white">
                  {isEditing ? "Editar chamado" : "Detalhes do chamado"}
                </h1>

                <p className="mt-2 text-sm text-slate-400">
                  {isEditing
                    ? "Atualize as informações do chamado."
                    : "Consulte as informações completas do chamado."}
                </p>
              </div>

              {!isEditing && (
                <button
                  type="button"
                  onClick={() => setEditingTicketId(ticket.id)}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500"
                >
                  <Pencil size={16} />
                  Editar chamado
                </button>
              )}
            </div>

            {isEditing ? (
              <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
                <EditTicketForm
                  key={ticket.id}
                  ticket={ticket}
                  onCancel={() => setEditingTicketId(null)}
                  onSuccess={() => setEditingTicketId(null)}
                />
              </section>
            ) : (
              <section className="space-y-6 rounded-xl border border-slate-800 bg-slate-900 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Hash size={16} />
                      Chamado #{ticket.id}
                    </div>

                    <h2 className="text-xl font-semibold text-white">
                      {ticket.title}
                    </h2>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <TicketStatusBadge status={ticket.status} />
                    <TicketPriorityBadge priority={ticket.priority} />
                  </div>
                </div>

                <div className="border-t border-slate-800 pt-6">
                  <h3 className="text-sm font-semibold text-slate-200">
                    Descrição
                  </h3>

                  <p className="mt-3 whitespace-pre-wrap wrap-break-word text-sm leading-7 text-slate-400">
                    {ticket.description}
                  </p>
                </div>

                <div className="grid gap-6 border-t border-slate-800 pt-6 sm:grid-cols-2">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <CalendarDays size={16} />
                      Criado em
                    </div>

                    <p className="text-sm font-medium text-white">
                      {formatDate(ticket.createdAt)}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <CalendarDays size={16} />
                      Última atualização
                    </div>

                    <p className="text-sm font-medium text-white">
                      {formatDate(ticket.updatedAt)}
                    </p>
                  </div>
                </div>
              </section>
            )}
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
