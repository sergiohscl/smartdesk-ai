import type { Ticket } from "@/types/ticket.types";

export const mockTickets: Ticket[] = [
  {
    id: "TCK-001",
    title: "Erro ao acessar o sistema",
    description: "Usuário não consegue realizar login.",
    status: "open",
    priority: "high",
    createdAt: "2026-10-25T09:30:00",
    updatedAt: "2026-10-25T09:30:00",
  },
  {
    id: "TCK-002",
    title: "Problema com impressora",
    description: "Impressora não responde aos comandos.",
    status: "in_progress",
    priority: "medium",
    createdAt: "2026-10-26T10:15:00",
    updatedAt: "2026-10-27T14:20:00",
  },
  {
    id: "TCK-003",
    title: "Instalação de software",
    description: "Solicitação de instalação de aplicativo.",
    status: "resolved",
    priority: "low",
    createdAt: "2026-10-27T08:00:00",
    updatedAt: "2026-10-28T16:00:00",
  },
  {
    id: "TCK-004",
    title: "Servidor indisponível",
    description: "Servidor principal não responde.",
    status: "open",
    priority: "critical",
    createdAt: "2026-10-29T11:45:00",
    updatedAt: "2026-10-29T11:45:00",
  },
];