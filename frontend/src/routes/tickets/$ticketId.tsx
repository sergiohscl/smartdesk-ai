
import {
  createFileRoute,
  redirect,
} from "@tanstack/react-router";

import { TicketDetailsPage } from "@/app/pages/TicketDetailsPage";

export const Route = createFileRoute("/tickets/$ticketId")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: "/login",
      });
    }
  },
  component: TicketDetailsPage,
});
