import {
  createRootRouteWithContext,
  Outlet,
} from "@tanstack/react-router";

import type { AppRouterContext } from "@/app/router/routerContext";

export const Route = createRootRouteWithContext<AppRouterContext>()({
  component: () => <Outlet />,
});
