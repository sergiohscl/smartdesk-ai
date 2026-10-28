import {
  createFileRoute,
  redirect,
} from "@tanstack/react-router";

import { HomePage } from "@/app/pages/HomePage";

export const Route = createFileRoute("/")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: "/login",
      });
    }
  },
  component: HomePage,
});
