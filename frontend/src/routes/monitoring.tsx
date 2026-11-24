import { createFileRoute, redirect } from "@tanstack/react-router";

import { MonitoringPage } from "@/app/pages/MonitoringPage";
import { canAccessMonitoring } from "@/utils/monitoringPermissions";

export const Route = createFileRoute("/monitoring")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: "/login",
      });
    }

    if (!canAccessMonitoring(context.auth.user)) {
      throw redirect({
        to: "/",
      });
    }
  },
  component: MonitoringPage,
});
