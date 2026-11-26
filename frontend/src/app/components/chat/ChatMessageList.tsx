import { useEffect, useRef } from "react";

import { ChatMessage } from "./ChatMessage";

import type {
  ChatMessage as ChatMessageData,
} from "@/types/chat.types";

interface ChatMessageListProps {
  messages: ChatMessageData[];
  pendingQuestion: string | null;
  streamingContent: string;
  isGenerating: boolean;
  assistantMessageId: number | null;
  userMessageId: number | null;
  onRegenerate: (messageId: number) => void;
  canRegenerate: boolean;
}

export function ChatMessageList({
  messages,
  pendingQuestion,
  streamingContent,
  isGenerating,
  assistantMessageId,
  userMessageId,
  onRegenerate,
  canRegenerate,
}: ChatMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const followRef = useRef(true);

  const ordered = [...messages].sort(
    (first, second) => first.id - second.id,
  );

  const latestQuestion = ordered.findLast(
    (message) => message.role === "user",
  );

  const regenerationTarget = ordered.findLast(
    (message) =>
      message.role === "assistant" &&
      message.status === "completed" &&
      message.is_active &&
      message.reply_to_message_id === latestQuestion?.id,
  );

  const showPendingQuestion =
    pendingQuestion !== null &&
    !messages.some((message) => message.id === userMessageId);

  useEffect(() => {
    if (followRef.current) {
      bottomRef.current?.scrollIntoView({ block: "end" });
    }
  }, [messages, streamingContent, pendingQuestion, isGenerating]);

  return (
    <div
      ref={containerRef}
      onScroll={() => {
        const element = containerRef.current;

        if (element) {
          followRef.current =
            element.scrollHeight -
              element.scrollTop -
              element.clientHeight <
            100;
        }
      }}
      className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6"
    >
      <div className="mx-auto max-w-3xl space-y-6">
        {ordered.map((message) => {
          if (
            isGenerating &&
            message.id === assistantMessageId
          ) {
            return null;
          }

          return (
            <ChatMessage
              key={message.id}
              role={message.role}
              content={message.content}
              status={message.status}
              onRegenerate={
                canRegenerate &&
                message.id === regenerationTarget?.id
                  ? () => onRegenerate(message.id)
                  : undefined
              }
            />
          );
        })}

        {showPendingQuestion && (
          <ChatMessage
            role="user"
            content={pendingQuestion}
            status="completed"
          />
        )}

        {isGenerating && (
          <ChatMessage
            role="assistant"
            content={streamingContent}
            status="pending"
          />
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
