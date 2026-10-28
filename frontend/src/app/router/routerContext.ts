
import type { UserPublic } from "@/types/auth.types";

export interface RouterAuthContext {
  user: UserPublic | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AppRouterContext {
  auth: RouterAuthContext;
}
