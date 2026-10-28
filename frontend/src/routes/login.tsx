import { createFileRoute } from "@tanstack/react-router";

import { LoginPage } from "@/app/pages/LoginPage";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});