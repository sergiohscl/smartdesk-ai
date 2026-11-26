import { createFileRoute, redirect } from "@tanstack/react-router";

import { ChatPage } from "@/app/pages/ChatPage";

export const Route = createFileRoute("/chat")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: "/login",
      });
    }
  },
  component: ChatPage,
});
