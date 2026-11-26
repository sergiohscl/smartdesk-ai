import { useRef, useState } from "react";

import { DashboardLayout } from "@/app/components/DashboardLayout/DashboardLayout";
import { ChatSidebar } from "@/app/components/chat/ChatSidebar";
import { ChatHeader } from "@/app/components/chat/ChatHeader";
import { ChatEmptyState } from "@/app/components/chat/ChatEmptyState";
import { ChatComposer } from "@/app/components/chat/ChatComposer";
import { ChatMessageList } from "@/app/components/chat/ChatMessageList";

import {
  useChatConversation,
  useChatConversations,
  useCreateChatConversation,
  useUpdateChatConversation,
  useDeleteChatConversation,
} from "@/hooks/useChatConversations";

import { useChatMessages } from "@/hooks/useChatMessages";
import { useChatGeneration } from "@/hooks/useChatGeneration";
import { useChatUsage } from "@/hooks/useChatUsage";

export function ChatPage() {
  const [selectedId, setSelectedId] = useState(0);
  const [conversationPage, setConversationPage] = useState(1);
  const [messagePage, setMessagePage] = useState(1);
  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const actionRef = useRef(false);

  const conversations = useChatConversations({
    page: conversationPage,
    pageSize: 20,
  });

  const conversation = useChatConversation(selectedId);

  const messages = useChatMessages(selectedId, {
    page: messagePage,
    pageSize: 50,
  });

  const usage = useChatUsage();
  const generation = useChatGeneration();

  const createConversation = useCreateChatConversation();
  const updateConversation = useUpdateChatConversation();
  const deleteConversation = useDeleteChatConversation();

  const busy =
    isSubmitting ||
    generation.isGenerating ||
    createConversation.isPending ||
    updateConversation.isPending ||
    deleteConversation.isPending;

  const remoteBusy =
    conversation.data?.generation_status === "generating";

  const limitReached = usage.data?.remaining === 0;

  const selectConversation = (id: number) => {
    if (actionRef.current || busy) return;

    generation.reset();
    setSelectedId(id);
    setMessagePage(1);
    setDraft("");
    setError(null);
    setPendingQuestion(null);
  };

  const handleCreate = async () => {
    if (actionRef.current || busy) return;

    actionRef.current = true;
    setError(null);

    try {
      const result = await createConversation.mutateAsync({});

      generation.reset();
      setSelectedId(result.conversation.id);
      setConversationPage(1);
      setMessagePage(1);
      setDraft("");
    } catch {
      setError("Não foi possível criar a conversa.");
    } finally {
      actionRef.current = false;
    }
  };

  const handleSend = async () => {
    const content = draft.trim();

    if (
      !content ||
      content.length > 8000 ||
      busy ||
      remoteBusy ||
      limitReached ||
      actionRef.current
    ) {
      return;
    }

    actionRef.current = true;
    setIsSubmitting(true);
    setError(null);

    try {
      let conversationId = selectedId;

      if (!conversationId) {
        const result = await createConversation.mutateAsync({});

        conversationId = result.conversation.id;
        setSelectedId(conversationId);
        setConversationPage(1);
      }

      setMessagePage(1);
      setPendingQuestion(content);
      setDraft("");

      await generation.sendMessage(conversationId, content);
    } catch {
      setDraft(content);
      setError(
        "Não foi possível concluir o envio. Confira o histórico antes de tentar novamente.",
      );
    } finally {
      setPendingQuestion(null);
      setIsSubmitting(false);
      actionRef.current = false;
    }
  };

  const handleRegenerate = async (messageId: number) => {
    if (
      !selectedId ||
      busy ||
      remoteBusy ||
      limitReached ||
      actionRef.current
    ) {
      return;
    }

    actionRef.current = true;
    setIsSubmitting(true);
    setError(null);

    try {
      await generation.regenerateMessage(selectedId, messageId);
    } catch {
      setError("Não foi possível regenerar a resposta.");
    } finally {
      setIsSubmitting(false);
      actionRef.current = false;
    }
  };

  const handleCancel = async () => {
    try {
      await generation.cancel();
    } catch {
      setError("Não foi possível cancelar a geração.");
    }
  };

  const handleRename = async () => {
    if (
      !conversation.data ||
      busy ||
      remoteBusy ||
      actionRef.current
    ) {
      return;
    }

    const title = window.prompt(
      "Novo título da conversa:",
      conversation.data.title,
    )?.trim();

    if (!title) return;

    if (title.length > 150) {
      setError("O título deve possuir até 150 caracteres.");
      return;
    }

    actionRef.current = true;
    setError(null);

    try {
      await updateConversation.mutateAsync({
        conversationId: selectedId,
        payload: { title },
      });
    } catch {
      setError("Não foi possível renomear a conversa.");
    } finally {
      actionRef.current = false;
    }
  };

  const handleDelete = async () => {
    if (
      !selectedId ||
      busy ||
      remoteBusy ||
      actionRef.current
    ) {
      return;
    }

    if (
      !window.confirm(
        "Excluir permanentemente esta conversa e suas mensagens?",
      )
    ) {
      return;
    }

    actionRef.current = true;
    setError(null);

    try {
      await deleteConversation.mutateAsync(selectedId);

      generation.reset();
      setSelectedId(0);
      setConversationPage(1);
      setMessagePage(1);
      setDraft("");
    } catch {
      setError("Não foi possível excluir a conversa.");
    } finally {
      actionRef.current = false;
    }
  };

  const items = messages.data?.items ?? [];

  const selectedUnavailable =
    selectedId > 0 &&
    (
      conversation.isPending ||
      conversation.isError ||
      messages.isPending ||
      messages.isError
    );

  const showEmpty =
    items.length === 0 &&
    !pendingQuestion &&
    !generation.isGenerating &&
    !selectedUnavailable;

  const generationError =
    generation.conversationId === selectedId &&
    generation.error
      ? "A geração encontrou um problema. Verifique o histórico da conversa."
      : null;

  return (
    <DashboardLayout>
      <div className="space-y-3">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Assistente IA
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Suporte técnico inteligente com processamento local.
          </p>
        </div>

        <div className="grid min-w-0 gap-3 xl:grid-cols-[240px_minmax(0,1fr)]">
          <ChatSidebar
            conversations={conversations.data?.items ?? []}
            selectedId={selectedId}
            usage={usage.data}
            onSelect={selectConversation}
            onCreate={() => void handleCreate()}
            onPageChange={setConversationPage}
            page={conversationPage}
            pages={conversations.data?.pages ?? 0}
            disabled={busy}
            isLoading={conversations.isPending}
            isError={conversations.isError}
            onRetry={() => void conversations.refetch()}
          />

          <section className="flex h-[calc(100dvh-200px)] min-h-[420px] min-w-0 flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
            <ChatHeader
              title={conversation.data?.title ?? "Nova conversa"}
              disabled={busy || remoteBusy || selectedUnavailable}
              hasConversation={selectedId > 0}
              onBackToHelp={() => selectConversation(0)}
              backDisabled={busy}
              onRename={() => void handleRename()}
              onDelete={() => void handleDelete()}
            />

            {(error || generationError) && (
              <div
                role="alert"
                className="border-b border-red-900/40 bg-red-950/20 p-3 text-sm text-red-300"
              >
                {error ?? generationError}
              </div>
            )}

            {remoteBusy && !generation.isGenerating && (
              <p role="status" className="p-3 text-xs text-amber-400">
                Existe uma geração em andamento nesta conversa.
                Aguardando atualização.
              </p>
            )}

            {selectedId > 0 &&
              (conversation.isError || messages.isError) && (
                <div role="alert" className="p-6 text-sm text-red-300">
                  Não foi possível carregar a conversa.

                  <button
                    type="button"
                    onClick={() => {
                      void conversation.refetch();
                      void messages.refetch();
                    }}
                    className="ml-3 underline"
                  >
                    Tentar novamente
                  </button>
                </div>
              )}

            {selectedId > 0 &&
              selectedUnavailable &&
              !conversation.isError &&
              !messages.isError &&
              !generation.isGenerating && (
                <p role="status" className="p-6 text-sm text-slate-400">
                  Carregando mensagens...
                </p>
              )}

            {(messages.data?.pages ?? 0) > 1 && (
              <div className="flex items-center justify-center gap-5 border-b border-slate-800 p-3 text-xs text-slate-400">
                <button
                  type="button"
                  disabled={busy || messagePage <= 1}
                  onClick={() => setMessagePage((page) => page - 1)}
                  className="disabled:opacity-40"
                >
                  Mais recentes
                </button>

                <span>
                  {messagePage}/{messages.data?.pages}
                </span>

                <button
                  type="button"
                  disabled={
                    busy ||
                    messagePage >= (messages.data?.pages ?? 0)
                  }
                  onClick={() => setMessagePage((page) => page + 1)}
                  className="disabled:opacity-40"
                >
                  Mais antigas
                </button>
              </div>
            )}

            {showEmpty ? (
              <div className="flex min-h-0 flex-1 items-start overflow-y-auto">
                <ChatEmptyState
                  onSuggestion={setDraft}
                  disabled={busy || remoteBusy || limitReached}
                />
              </div>
            ) : (
              <ChatMessageList
                key={selectedId}
                messages={items}
                pendingQuestion={pendingQuestion}
                streamingContent={generation.content}
                isGenerating={generation.isGenerating}
                assistantMessageId={generation.assistantMessageId}
                userMessageId={generation.userMessageId}
                canRegenerate={
                  !busy &&
                  !remoteBusy &&
                  !limitReached &&
                  !selectedUnavailable &&
                  messagePage === 1
                }
                onRegenerate={(id) => void handleRegenerate(id)}
              />
            )}

            <div className="border-t border-slate-800 p-4">
              <ChatComposer
                value={draft}
                onChange={setDraft}
                onSend={() => void handleSend()}
                onCancel={() => void handleCancel()}
                isGenerating={generation.isGenerating}
                canCancel={generation.canCancel}
                disabled={
                  busy ||
                  remoteBusy ||
                  limitReached ||
                  selectedUnavailable
                }
              />
            </div>
          </section>
        </div>
      </div>
    </DashboardLayout>
  );
}
