import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/app/providers/AuthProvider";
import { authToken } from "@/lib/authToken";
import { chatQueryKeys } from "@/lib/chatQueryKeys";
import { chatService } from "@/services/chatService";
import { chatStream } from "@/services/chatStream";

import type {
  ChatStreamEvent,
  ChatTerminalEvent,
} from "@/types/chat.types";

type GenerationPhase =
  | "idle"
  | "connecting"
  | "streaming"
  | "cancelling"
  | "completed"
  | "cancelled"
  | "truncated"
  | "failed"
  | "interrupted";

interface GenerationState {
  phase: GenerationPhase;
  conversationId: number | null;
  generationId: string | null;
  assistantMessageId: number | null;
  userMessageId: number | null;
  content: string;
  error: string | null;
  terminal: ChatTerminalEvent | null;
}

interface ActiveGeneration {
  controller: AbortController;
  conversationId: number;
  generationId: string | null;
  token: string;
  cancelling: boolean;
}

const INITIAL_STATE: GenerationState = {
  phase: "idle",
  conversationId: null,
  generationId: null,
  assistantMessageId: null,
  userMessageId: null,
  content: "",
  error: null,
  terminal: null,
};

export function useChatGeneration() {
  const { user, logout } = useAuth();
  const userId = user?.id ?? 0;
  const queryClient = useQueryClient();

  const [state, setState] =
    useState<GenerationState>(INITIAL_STATE);

  const activeRef = useRef<ActiveGeneration | null>(null);

  useEffect(() => {
    return () => {
      const active = activeRef.current;
      activeRef.current = null;
      active?.controller.abort();
    };
  }, [userId]);

  const reconcile = useCallback(
    async (conversationId: number) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: chatQueryKeys.conversations(userId),
        }),
        queryClient.invalidateQueries({
          queryKey: chatQueryKeys.conversation(
            userId,
            conversationId,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: chatQueryKeys.messages(
            userId,
            conversationId,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: chatQueryKeys.usage(userId),
        }),
      ]);
    },
    [queryClient, userId],
  );

  const start = useCallback(
    async (
      conversationId: number,
      request:
        | { content: string }
        | { messageId: number },
    ): Promise<ChatTerminalEvent> => {
      const token = authToken.get();

      if (!token || !userId) {
        throw new Error("Sessão não autenticada.");
      }

      if (activeRef.current) {
        throw new Error("Já existe uma geração em andamento.");
      }

      if (
        !Number.isSafeInteger(conversationId) ||
        conversationId <= 0
      ) {
        throw new Error("Conversa inválida.");
      }

      const active: ActiveGeneration = {
        controller: new AbortController(),
        conversationId,
        generationId: null,
        token,
        cancelling: false,
      };

      activeRef.current = active;

      setState({
        ...INITIAL_STATE,
        phase: "connecting",
        conversationId,
      });

      const isCurrent = () =>
        activeRef.current === active &&
        authToken.get() === token;

      const onEvent = (event: ChatStreamEvent) => {
        if (!isCurrent()) return;

        if (event.type === "message.created") {
          active.generationId = event.generation_id;

          setState((previous) => ({
            ...previous,
            phase: "streaming",
            generationId: event.generation_id,
            assistantMessageId: event.assistant_message_id,
            userMessageId: event.user_message_id,
          }));

          return;
        }

        if (event.type === "response.delta") {
          setState((previous) => ({
            ...previous,
            content: previous.content + event.delta,
          }));

          return;
        }

        if (event.type === "response.error") {
          setState((previous) => ({
            ...previous,
            phase: "interrupted",
            error: event.error_code,
            terminal: event,
          }));

          return;
        }

        setState((previous) => ({
          ...previous,
          phase:
            event.type === "response.completed"
              ? "completed"
              : event.type === "response.cancelled"
                ? "cancelled"
                : event.type === "response.truncated"
                  ? "truncated"
                  : "failed",
          content: event.message.content,
          error:
            event.type === "response.failed"
              ? event.error_code
              : null,
          terminal: event,
        }));
      };

      const options = {
        signal: active.controller.signal,
        onEvent,
        onUnauthorized: logout,
      };

      try {
        if ("content" in request) {
          return await chatStream.sendMessage(
            conversationId,
            { content: request.content },
            options,
          );
        }

        return await chatStream.regenerateMessage(
          conversationId,
          request.messageId,
          options,
        );
      } catch (error) {
        if (isCurrent()) {
          setState((previous) => ({
            ...previous,
            phase: "interrupted",
            error: "Não foi possível concluir a geração.",
          }));
        }

        throw error;
      } finally {
        if (activeRef.current === active) {
          try {
            if (authToken.get() === token) {
              await reconcile(conversationId);
            }
          } finally {
            if (activeRef.current === active) {
              activeRef.current = null;
            }
          }
        }
      }
    },
    [logout, reconcile, userId],
  );

  const sendMessage = useCallback(
    (conversationId: number, content: string) =>
      start(conversationId, { content }),
    [start],
  );

  const regenerateMessage = useCallback(
    (conversationId: number, messageId: number) =>
      start(conversationId, { messageId }),
    [start],
  );

  const cancel = useCallback(async () => {
    const active = activeRef.current;

    if (
      !active ||
      !active.generationId ||
      active.cancelling ||
      authToken.get() !== active.token
    ) {
      return;
    }

    active.cancelling = true;

    setState((previous) => ({
      ...previous,
      phase: "cancelling",
    }));

    try {
      await chatService.cancelGeneration(
        active.conversationId,
        { generation_id: active.generationId },
      );
    } catch (error) {
      if (
        activeRef.current === active &&
        authToken.get() === active.token
      ) {
        active.cancelling = false;

        setState((previous) =>
          previous.phase === "cancelling"
            ? {
                ...previous,
                phase: "streaming",
                error: "Não foi possível cancelar a geração.",
              }
            : previous,
        );
      }

      throw error;
    }
  }, []);

  const disconnect = useCallback(() => {
    activeRef.current?.controller.abort();
  }, []);

  const reset = useCallback(() => {
    if (!activeRef.current) {
      setState(INITIAL_STATE);
    }
  }, []);

  const isGenerating =
    state.phase === "connecting" ||
    state.phase === "streaming" ||
    state.phase === "cancelling";

  return {
    ...state,
    isGenerating,
    canCancel:
      state.phase === "streaming" &&
      state.generationId !== null,
    sendMessage,
    regenerateMessage,
    cancel,
    disconnect,
    reset,
  };
}
