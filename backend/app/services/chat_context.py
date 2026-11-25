from collections.abc import Sequence

from app.core.settings import Settings
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.services.chat_prompts import build_system_message
from app.services.providers.base import (
    ProviderMessage,
    ProviderRequest,
    ProviderRole,
)

MESSAGE_TOKEN_OVERHEAD = 16
CONTEXT_TOKEN_OVERHEAD = 64

type ChatTurn = tuple[ProviderMessage, ProviderMessage]


class ChatContextError(ValueError):
    """Invalid or oversized chat context."""


def estimate_message_tokens(message: ProviderMessage) -> int:
    """Estimate tokens conservatively using UTF-8 bytes."""

    return len(message.content.encode('utf-8')) + MESSAGE_TOKEN_OVERHEAD


def _to_provider_message(message: ChatMessage) -> ProviderMessage:
    return ProviderMessage(
        role=ProviderRole(message.role.value),
        content=message.content,
    )


def _is_completed_active(message: ChatMessage) -> bool:
    return message.status == ChatMessageStatus.COMPLETED and message.is_active


def _validate_history(
    current_message: ChatMessage,
    history: Sequence[ChatMessage],
) -> None:
    if any(
        message.conversation_id != current_message.conversation_id
        for message in history
    ):
        raise ChatContextError(
            'History contains messages from another conversation.',
        )

    ids = [message.id for message in history]

    if len(ids) != len(set(ids)):
        raise ChatContextError(
            'History contains duplicate messages.',
        )


def _collect_turns(
    current_message: ChatMessage,
    history: Sequence[ChatMessage],
) -> list[ChatTurn]:
    users = {}
    replies = {}

    for message in history:
        if not _is_completed_active(message):
            continue

        if message.role == ChatMessageRole.USER:
            if message.id < current_message.id:
                users[message.id] = message

        elif message.role == ChatMessageRole.ASSISTANT:
            reply_id = message.reply_to_message_id

            if reply_id is None or reply_id >= current_message.id:
                continue

            if reply_id in replies:
                raise ChatContextError(
                    'Multiple active replies for one message.',
                )

            replies[reply_id] = message

    return [
        (
            _to_provider_message(users[user_id]),
            _to_provider_message(replies[user_id]),
        )
        for user_id in sorted(users)
        if user_id in replies
    ]


class ChatContext:
    """Build bounded provider requests from chat history."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _validate_current(
        self,
        message: ChatMessage,
    ) -> None:
        if message.role != ChatMessageRole.USER or not _is_completed_active(
            message
        ):
            raise ChatContextError(
                'Current message must be an active user message.',
            )

        if len(message.content) > self._settings.CHAT_MAX_MESSAGE_CHARS:
            raise ChatContextError(
                'Current message exceeds the character limit.',
            )

    def _select_history(
        self,
        turns: list[ChatTurn],
        remaining_budget: int,
    ) -> list[ProviderMessage]:
        selected = []

        max_turns = self._settings.CHAT_MAX_CONTEXT_MESSAGES // 2

        for turn in reversed(turns):
            if len(selected) >= max_turns:
                break

            cost = sum(estimate_message_tokens(message) for message in turn)

            if cost > remaining_budget:
                break

            selected.append(turn)
            remaining_budget -= cost

        return [message for turn in reversed(selected) for message in turn]

    def build(
        self,
        *,
        current_message: ChatMessage,
        history: Sequence[ChatMessage],
    ) -> ProviderRequest:
        self._validate_current(current_message)
        _validate_history(current_message, history)

        system = build_system_message(
            self._settings.CHAT_PROMPT_VERSION,
        )
        current = _to_provider_message(current_message)

        remaining_budget = (
            self._settings.chat_input_token_budget
            - CONTEXT_TOKEN_OVERHEAD
            - estimate_message_tokens(system)
            - estimate_message_tokens(current)
        )

        if remaining_budget < 0:
            raise ChatContextError(
                'Current message exceeds the context budget.',
            )

        turns = _collect_turns(current_message, history)

        selected = self._select_history(
            turns,
            remaining_budget,
        )

        return ProviderRequest(
            messages=(system, *selected, current),
        )
