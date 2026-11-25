import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/app/providers/AuthProvider";
import { chatQueryKeys } from "@/lib/chatQueryKeys";
import { chatService } from "@/services/chatService";

import type {
  ChatPaginationParams,
} from "@/types/chat.types";

export function useChatMessages(
  conversationId: number,
  {
    page = 1,
    pageSize = 50,
  }: ChatPaginationParams = {},
) {
  const { user } = useAuth();
  const userId = user?.id ?? 0;

  return useQuery({
    queryKey: chatQueryKeys.messageList(
      userId,
      conversationId,
      page,
      pageSize,
    ),
    queryFn: ({ signal }) =>
      chatService.getMessages(
        conversationId,
        { page, pageSize },
        signal,
      ),
    enabled:
      userId > 0 &&
      Number.isSafeInteger(conversationId) &&
      conversationId > 0,
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.items.some(
        (message) => message.status === "pending",
      )
        ? 3000
        : false,
  });
}
