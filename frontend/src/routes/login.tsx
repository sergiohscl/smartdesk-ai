import {
  createFileRoute,
  redirect,
} from "@tanstack/react-router";

import { LoginPage } from "@/app/pages/LoginPage";

export const Route = createFileRoute("/login")({
  beforeLoad: ({ context }) => {
    if (context.auth.isAuthenticated) {
      throw redirect({
        to: "/",
        replace: true,
      });
    }
  },
  component: LoginPage,
});
