import { useEffect } from "react";
import { RouterProvider } from "@tanstack/react-router";
import { LoaderCircle } from "lucide-react";

import { useAuth } from "@/app/providers/AuthProvider";
import { router } from "@/app/router";

export function AppRouterProvider() {
  const {
    user,
    isAuthenticated,
    isLoading,
    isInitializing,
  } = useAuth();

  useEffect(() => {
    if (!isInitializing) {
      void router.invalidate();
    }
  }, [user, isAuthenticated, isLoading, isInitializing]);

  if (isInitializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <LoaderCircle className="h-10 w-10 animate-spin text-blue-500" />

          <p className="text-sm text-slate-400">
            Restaurando sessão...
          </p>
        </div>
      </div>
    );
  }

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