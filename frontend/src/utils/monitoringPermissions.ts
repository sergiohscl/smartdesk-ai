import type { UserPublic } from "@/types/auth.types";

export function canAccessMonitoring(
  user: UserPublic | null | undefined,
): boolean {
  return (
    user?.role === "admin" ||
    user?.role === "support"
  );
}
