import { useEffect } from "react";
import { RouterProvider } from "@tanstack/react-router";

import { useAuth } from "@/app/providers/AuthProvider";
import { router } from "@/app/router";

export function AppRouterProvider() {
  const { user, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    void router.invalidate();
  }, [user, isAuthenticated, isLoading]);

  return (
    <RouterProvider
      router={router}
      context={{
        auth: {
          user,
          isAuthenticated,
          isLoading,
        },
      }}
    />
  );
}
