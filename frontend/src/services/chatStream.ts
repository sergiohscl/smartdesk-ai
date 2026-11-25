import { authToken } from "@/lib/authToken";

import type {
  ChatMessageCreate,
  ChatStreamEvent,
  ChatTerminalEvent,
} from "@/types/chat.types";

const MAX_FRAME_SIZE = 2 * 1024 * 1024;

const EVENT_TYPES = new Set([
  "message.created",
  "response.delta",
  "response.completed",
  "response.cancelled",
  "response.truncated",
  "response.failed",
  "response.error",
]);

export class ChatStreamError extends Error {
  readonly status: number | undefined;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ChatStreamError";
    this.status = status;
  }
}

export interface ChatStreamOptions {
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
  onUnauthorized?: () => void;
}

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPositiveId(value: unknown): boolean {
  return (
    typeof value === "number" &&
    Number.isSafeInteger(value) &&
    value > 0
  );
}

function parseFrame(
  frame: string,
): ChatStreamEvent | null {
  let eventName = "";
  const data: string[] = [];

  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    }

    if (line.startsWith("data:")) {
      data.push(line.slice(5).replace(/^ /, ""));
    }
  }

  if (data.length === 0) {
    return null;
  }

  let payload: unknown;

  try {
    payload = JSON.parse(data.join("\n"));
  } catch {
    throw new ChatStreamError(
      "Evento SSE contém JSON inválido.",
    );
  }

  if (
    !isRecord(payload) ||
    typeof payload.type !== "string" ||
    !EVENT_TYPES.has(payload.type) ||
    payload.type !== eventName ||
    !isPositiveId(payload.conversation_id) ||
    !isPositiveId(payload.assistant_message_id) ||
    typeof payload.generation_id !== "string"
  ) {
    throw new ChatStreamError(
      "Evento SSE inválido.",
    );
  }

  if (
    payload.type === "response.delta" &&
    (
      typeof payload.delta !== "string" ||
      payload.delta.length === 0
    )
  ) {
    throw new ChatStreamError(
      "Fragmento SSE inválido.",
    );
  }

  if (
    payload.type === "message.created" &&
    !isPositiveId(payload.user_message_id)
  ) {
    throw new ChatStreamError(
      "Identificador de mensagem inválido.",
    );
  }

  if (
    payload.type === "response.error" &&
    payload.error_code !== "PERSISTENCE_ERROR" &&
    payload.error_code !== "GENERATION_CONFLICT"
  ) {
    throw new ChatStreamError(
      "Erro de persistência inválido.",
    );
  }

  if (
    payload.type !== "message.created" &&
    payload.type !== "response.delta" &&
    payload.type !== "response.error"
  ) {
    const message = payload.message;

    if (
      !isRecord(message) ||
      message.id !== payload.assistant_message_id ||
      message.conversation_id !== payload.conversation_id ||
      message.generation_id !== payload.generation_id ||
      message.role !== "assistant" ||
      typeof message.content !== "string"
    ) {
      throw new ChatStreamError(
        "Mensagem terminal inválida.",
      );
    }
  }

  return payload as unknown as ChatStreamEvent;
}

function isTerminal(
  event: ChatStreamEvent,
): event is ChatTerminalEvent {
  return (
    event.type !== "message.created" &&
    event.type !== "response.delta"
  );
}

async function streamRequest(
  conversationId: number,
  path: string,
  options: ChatStreamOptions,
  payload?: ChatMessageCreate,
): Promise<ChatTerminalEvent> {
  const token = authToken.get();

  if (!token) {
    options.onUnauthorized?.();

    throw new ChatStreamError(
      "Sessão não autenticada.",
      401,
    );
  }

  const baseUrl = (
    import.meta.env.VITE_API_URL || "/api/v1"
  ).replace(/\/+$/, "");

  const response = await fetch(
    `${baseUrl}/chat${path}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      body: payload
        ? JSON.stringify(payload)
        : undefined,
      signal: options.signal,
      cache: "no-store",
      redirect: "error",
    },
  );

  if (response.status === 401) {
    if (authToken.get() === token) {
      options.onUnauthorized?.();
    }

    throw new ChatStreamError(
      "Sessão expirada.",
      401,
    );
  }

  if (!response.ok) {
    throw new ChatStreamError(
      "Não foi possível iniciar a geração.",
      response.status,
    );
  }

  if (
    !response.body ||
    !response.headers
      .get("content-type")
      ?.includes("text/event-stream")
  ) {
    throw new ChatStreamError(
      "Resposta de streaming inválida.",
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", {
    fatal: true,
  });

  let buffer = "";
  let generationId: string | null = null;
  let assistantMessageId: number | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (
        authToken.get() !== token ||
        options.signal?.aborted
      ) {
        throw new DOMException(
          "Streaming interrompido.",
          "AbortError",
        );
      }

      buffer += done
        ? decoder.decode()
        : decoder.decode(value, { stream: true });

      let separator = /\r?\n\r?\n/.exec(buffer);

      while (separator) {
        const frame = buffer.slice(
          0,
          separator.index,
        );

        buffer = buffer.slice(
          separator.index + separator[0].length,
        );

        if (frame.length > MAX_FRAME_SIZE) {
          throw new ChatStreamError(
            "Evento SSE excede o limite permitido.",
          );
        }

        const event = parseFrame(frame);

        if (event) {
          if (event.conversation_id !== conversationId) {
            throw new ChatStreamError(
              "Conversa do evento não corresponde à solicitação.",
            );
          }

          if (event.type === "message.created") {
            if (generationId !== null) {
              throw new ChatStreamError(
                "Geração duplicada no streaming.",
              );
            }

            generationId = event.generation_id;
            assistantMessageId =
              event.assistant_message_id;
          } else if (
            generationId === null ||
            event.generation_id !== generationId ||
            event.assistant_message_id !==
              assistantMessageId
          ) {
            throw new ChatStreamError(
              "Identidade da geração inválida.",
            );
          }

          options.onEvent(event);

          if (isTerminal(event)) {
            return event;
          }
        }

        separator = /\r?\n\r?\n/.exec(buffer);
      }

      if (buffer.length > MAX_FRAME_SIZE) {
        throw new ChatStreamError(
          "Buffer SSE excede o limite permitido.",
        );
      }

      if (done) {
        break;
      }
    }

    throw new ChatStreamError(
      "Streaming encerrado sem evento terminal.",
    );
  } finally {
    try {
      await reader.cancel();
    } catch {
      // A conexão pode já estar encerrada.
    } finally {
      reader.releaseLock();
    }
  }
}

export const chatStream = {
  sendMessage(
    conversationId: number,
    payload: ChatMessageCreate,
    options: ChatStreamOptions,
  ): Promise<ChatTerminalEvent> {
    return streamRequest(
      conversationId,
      `/conversations/${conversationId}/messages`,
      options,
      payload,
    );
  },

  regenerateMessage(
    conversationId: number,
    messageId: number,
    options: ChatStreamOptions,
  ): Promise<ChatTerminalEvent> {
    return streamRequest(
      conversationId,
      `/conversations/${conversationId}/messages/${messageId}/regenerate`,
      options,
    );
  },
};
