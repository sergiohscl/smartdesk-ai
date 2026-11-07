import { createFileRoute, redirect } from "@tanstack/react-router";

import { TicketsPage } from "@/app/pages/TicketsPage";

export const Route = createFileRoute("/tickets/")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: "/login",
      });
    }
  },
  component: TicketsPage,
});
