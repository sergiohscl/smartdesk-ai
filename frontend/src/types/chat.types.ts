export type ChatGenerationStatus = "idle" | "generating";

export type ChatMessageRole = "user" | "assistant";

export type ChatMessageStatus =
  | "pending"
  | "completed"
  | "failed"
  | "cancelled"
  | "truncated";

export interface ChatConversation {
  id: number;
  title: string;
  generation_status: ChatGenerationStatus;
  generation_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatConversationCreate {
  title?: string | null;
}

export interface ChatConversationUpdate {
  title: string;
}

export interface ChatPaginationParams {
  page?: number;
  pageSize?: number;
}

export interface ChatPage<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type ChatConversationListResponse =
  ChatPage<ChatConversation>;

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: ChatMessageRole;
  content: string;
  status: ChatMessageStatus;
  model: string | null;
  generation_id: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  reply_to_message_id: number | null;
  regenerated_from_id: number | null;
  is_active: boolean;
  created_at: string;
  completed_at: string | null;
}

export interface ChatMessageCreate {
  content: string;
}

export type ChatMessageListResponse =
  ChatPage<ChatMessage>;

export interface ChatCancellationRequest {
  generation_id: string;
}

export interface ChatCancellationResponse {
  conversation_id: number;
  generation_id: string;
  cancellation_requested: true;
}

export interface ChatUsage {
  daily_limit: number;
  used: number;
  remaining: number;
  input_tokens: number;
  output_tokens: number;
  resets_at: string;
}

export type ChatStreamErrorCode =
  | "MODEL_NOT_FOUND"
  | "PROVIDER_REQUEST_ERROR"
  | "PROVIDER_UNAVAILABLE"
  | "GENERATION_TIMEOUT"
  | "INVALID_PROVIDER_RESPONSE"
  | "STREAM_INTERRUPTED"
  | "INTERNAL_ERROR"
  | "PERSISTENCE_ERROR"
  | "GENERATION_CONFLICT";

export interface ChatStreamEventBase {
  conversation_id: number;
  generation_id: string;
  assistant_message_id: number;
}

export interface ChatMessageCreatedEvent
  extends ChatStreamEventBase {
  type: "message.created";
  user_message_id: number;
  regenerated_from_id: number | null;
}

export interface ChatResponseDeltaEvent
  extends ChatStreamEventBase {
  type: "response.delta";
  delta: string;
}

export interface ChatTerminalEventBase
  extends ChatStreamEventBase {
  message: ChatMessage;
}

export interface ChatResponseCompletedEvent
  extends ChatTerminalEventBase {
  type: "response.completed";
}

export interface ChatResponseCancelledEvent
  extends ChatTerminalEventBase {
  type: "response.cancelled";
}

export interface ChatResponseTruncatedEvent
  extends ChatTerminalEventBase {
  type: "response.truncated";
}

export interface ChatResponseFailedEvent
  extends ChatTerminalEventBase {
  type: "response.failed";
  error_code: ChatStreamErrorCode;
}

export interface ChatResponseErrorEvent
  extends ChatStreamEventBase {
  type: "response.error";
  error_code:
    | "PERSISTENCE_ERROR"
    | "GENERATION_CONFLICT";
}

export type ChatStreamEvent =
  | ChatMessageCreatedEvent
  | ChatResponseDeltaEvent
  | ChatResponseCompletedEvent
  | ChatResponseCancelledEvent
  | ChatResponseTruncatedEvent
  | ChatResponseFailedEvent
  | ChatResponseErrorEvent;

export type ChatTerminalEvent = Exclude<
  ChatStreamEvent,
  ChatMessageCreatedEvent | ChatResponseDeltaEvent
>;
