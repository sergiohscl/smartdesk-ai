import type { UserPublic } from "@/types/auth.types";
import type { Ticket } from "@/types/ticket.types";

export function canManageTicket(
  user: UserPublic | null,
  ticket: Ticket,
): boolean {
  if (!user || !user.is_active) {
    return false;
  }

  if (user.role === "admin" || user.role === "support") {
    return true;
  }

  return user.role === "user" && ticket.createdById === user.id;
}
