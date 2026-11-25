import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { useAuth } from "@/app/providers/AuthProvider";
import { authToken } from "@/lib/authToken";
import { chatQueryKeys } from "@/lib/chatQueryKeys";
import { chatService } from "@/services/chatService";

import type {
  ChatConversationCreate,
  ChatConversationUpdate,
  ChatPaginationParams,
} from "@/types/chat.types";

export function useChatConversations({
  page = 1,
  pageSize = 20,
}: ChatPaginationParams = {}) {
  const { user } = useAuth();
  const userId = user?.id ?? 0;

  return useQuery({
    queryKey: chatQueryKeys.conversationList(
      userId,
      page,
      pageSize,
    ),
    queryFn: ({ signal }) =>
      chatService.getConversations(
        { page, pageSize },
        signal,
      ),
    enabled: userId > 0,
    staleTime: 10_000,
    retry: false,
  });
}

export function useChatConversation(
  conversationId: number,
) {
  const { user } = useAuth();
  const userId = user?.id ?? 0;

  return useQuery({
    queryKey: chatQueryKeys.conversation(
      userId,
      conversationId,
    ),
    queryFn: ({ signal }) =>
      chatService.getConversation(
        conversationId,
        signal,
      ),
    enabled:
      userId > 0 &&
      Number.isSafeInteger(conversationId) &&
      conversationId > 0,
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.generation_status === "generating"
        ? 3000
        : false,
  });
}

export function useCreateChatConversation() {
  const { user } = useAuth();
  const userId = user?.id ?? 0;
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: ChatConversationCreate,
    ) => {
      const token = authToken.get();

      if (!token || !userId) {
        throw new Error("Sessão não autenticada.");
      }

      const conversation =
        await chatService.createConversation(payload);

      return { conversation, token };
    },

    onSuccess: async ({ conversation, token }) => {
      if (authToken.get() !== token) return;

      queryClient.setQueryData(
        chatQueryKeys.conversation(
          userId,
          conversation.id,
        ),
        conversation,
      );

      await queryClient.invalidateQueries({
        queryKey: chatQueryKeys.conversations(userId),
      });
    },
  });
}

export function useUpdateChatConversation() {
  const { user } = useAuth();
  const userId = user?.id ?? 0;
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      conversationId,
      payload,
    }: {
      conversationId: number;
      payload: ChatConversationUpdate;
    }) => {
      const token = authToken.get();

      if (!token || !userId) {
        throw new Error("Sessão não autenticada.");
      }

      const conversation =
        await chatService.updateConversation(
          conversationId,
          payload,
        );

      return { conversation, token };
    },

    onSuccess: async ({ conversation, token }) => {
      if (authToken.get() !== token) return;

      queryClient.setQueryData(
        chatQueryKeys.conversation(
          userId,
          conversation.id,
        ),
        conversation,
      );

      await queryClient.invalidateQueries({
        queryKey: chatQueryKeys.conversations(userId),
      });
    },
  });
}

export function useDeleteChatConversation() {
  const { user } = useAuth();
  const userId = user?.id ?? 0;
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (conversationId: number) => {
      const token = authToken.get();

      if (!token || !userId) {
        throw new Error("Sessão não autenticada.");
      }

      await chatService.deleteConversation(conversationId);

      return { conversationId, token };
    },

    onSuccess: async ({ conversationId, token }) => {
      if (authToken.get() !== token) return;

      queryClient.removeQueries({
        queryKey: chatQueryKeys.conversation(
          userId,
          conversationId,
        ),
      });

      queryClient.removeQueries({
        queryKey: chatQueryKeys.messages(
          userId,
          conversationId,
        ),
      });

      await queryClient.invalidateQueries({
        queryKey: chatQueryKeys.conversations(userId),
      });
    },
  });
}
