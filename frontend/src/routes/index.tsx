import { createFileRoute, redirect } from "@tanstack/react-router";

import { DashboardPage } from "@/app/pages/DashboardPage";

export const Route = createFileRoute("/")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: "/login",
      });
    }
  },
  component: DashboardPage,
});