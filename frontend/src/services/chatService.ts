import { api } from "@/services/api";

import type {
  ChatCancellationRequest,
  ChatCancellationResponse,
  ChatConversation,
  ChatConversationCreate,
  ChatConversationListResponse,
  ChatConversationUpdate,
  ChatMessageListResponse,
  ChatPaginationParams,
  ChatUsage,
} from "@/types/chat.types";

const BASE_URL = "/chat";

export const chatService = {
  async createConversation(
    payload: ChatConversationCreate = {},
  ): Promise<ChatConversation> {
    const { data } = await api.post<ChatConversation>(
      `${BASE_URL}/conversations`,
      payload,
    );

    return data;
  },

  async getConversations(
    {
      page = 1,
      pageSize = 20,
    }: ChatPaginationParams = {},
    signal?: AbortSignal,
  ): Promise<ChatConversationListResponse> {
    const { data } =
      await api.get<ChatConversationListResponse>(
        `${BASE_URL}/conversations`,
        {
          params: {
            page,
            page_size: pageSize,
          },
          signal,
        },
      );

    return data;
  },

  async getConversation(
    conversationId: number,
    signal?: AbortSignal,
  ): Promise<ChatConversation> {
    const { data } = await api.get<ChatConversation>(
      `${BASE_URL}/conversations/${conversationId}`,
      { signal },
    );

    return data;
  },

  async updateConversation(
    conversationId: number,
    payload: ChatConversationUpdate,
  ): Promise<ChatConversation> {
    const { data } = await api.patch<ChatConversation>(
      `${BASE_URL}/conversations/${conversationId}`,
      payload,
    );

    return data;
  },

  async deleteConversation(
    conversationId: number,
  ): Promise<void> {
    await api.delete(
      `${BASE_URL}/conversations/${conversationId}`,
    );
  },

  async getMessages(
    conversationId: number,
    {
      page = 1,
      pageSize = 50,
    }: ChatPaginationParams = {},
    signal?: AbortSignal,
  ): Promise<ChatMessageListResponse> {
    const { data } =
      await api.get<ChatMessageListResponse>(
        `${BASE_URL}/conversations/${conversationId}/messages`,
        {
          params: {
            page,
            page_size: pageSize,
          },
          signal,
        },
      );

    return data;
  },

  async getUsage(
    signal?: AbortSignal,
  ): Promise<ChatUsage> {
    const { data } = await api.get<ChatUsage>(
      `${BASE_URL}/usage`,
      { signal },
    );

    return data;
  },

  async cancelGeneration(
    conversationId: number,
    payload: ChatCancellationRequest,
  ): Promise<ChatCancellationResponse> {
    const { data } =
      await api.post<ChatCancellationResponse>(
        `${BASE_URL}/conversations/${conversationId}/cancel`,
        payload,
      );

    return data;
  },
};
