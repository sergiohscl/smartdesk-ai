export const chatQueryKeys = {
  all: (userId: number) =>
    ["chat", userId] as const,

  conversations: (userId: number) =>
    ["chat", userId, "conversations"] as const,

  conversationList: (
    userId: number,
    page: number,
    pageSize: number,
  ) =>
    ["chat", userId, "conversations", page, pageSize] as const,

  conversation: (
    userId: number,
    conversationId: number,
  ) =>
    ["chat", userId, "conversation", conversationId] as const,

  messages: (
    userId: number,
    conversationId: number,
  ) =>
    ["chat", userId, "messages", conversationId] as const,

  messageList: (
    userId: number,
    conversationId: number,
    page: number,
    pageSize: number,
  ) =>
    [
      "chat",
      userId,
      "messages",
      conversationId,
      page,
      pageSize,
    ] as const,

  usage: (userId: number) =>
    ["chat", userId, "usage"] as const,
};
