import { createRouter } from "@tanstack/react-router";

import { routeTree } from "@/routeTree.gen";

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  context: {
    auth: {
      user: null,
      isAuthenticated: false,
      isLoading: false,
    },
  },
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
