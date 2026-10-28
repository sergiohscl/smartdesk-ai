import {
  createFileRoute,
  redirect,
} from "@tanstack/react-router";

import { RegisterPage } from "@/app/pages/RegisterPage";

export const Route = createFileRoute("/register")({
  beforeLoad: ({ context }) => {
    if (context.auth.isAuthenticated) {
      throw redirect({
        to: "/",
        replace: true,
      });
    }
  },
  component: RegisterPage,
});
