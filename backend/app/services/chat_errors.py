from app.schemas.chat import ChatStreamErrorCode
from app.services.providers.exceptions import ProviderError


def map_chat_error(error: Exception) -> ChatStreamErrorCode:
    """Convert generation failures into safe public error codes."""

    if isinstance(error, ProviderError):
        return ChatStreamErrorCode(error.code.value)

    if isinstance(error, TimeoutError):
        return ChatStreamErrorCode.GENERATION_TIMEOUT

    return ChatStreamErrorCode.INTERNAL_ERROR


class ChatConversationNotFoundError(Exception):
    """Conversation does not exist or is not accessible."""

    def __init__(self) -> None:
        super().__init__('Conversation not found.')


class ChatConversationBusyError(Exception):
    """Conversation has an active generation."""

    def __init__(self) -> None:
        super().__init__('Conversation has an active generation.')


class ChatDisabledError(Exception):
    """Chat generation is disabled."""


class ChatDailyLimitError(Exception):
    """Daily generation quota has been reached."""


class ChatRateLimitError(Exception):
    """Generation request rate has been exceeded."""


class ChatUserConcurrencyError(Exception):
    """User generation concurrency limit has been reached."""


class ChatGlobalConcurrencyError(Exception):
    """Global generation capacity has been reached."""


class ChatGenerationConflictError(Exception):
    """Generation is no longer active or cannot be finalized."""

    def __init__(self) -> None:
        super().__init__('Generation is no longer active.')


class ChatRegenerationConflictError(Exception):
    """The selected message cannot be regenerated."""

    def __init__(self) -> None:
        super().__init__('The selected message cannot be regenerated.')
