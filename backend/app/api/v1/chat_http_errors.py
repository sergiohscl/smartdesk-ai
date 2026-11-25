from fastapi import HTTPException, status

from app.services.chat_errors import (
    ChatConversationBusyError,
    ChatConversationNotFoundError,
    ChatDailyLimitError,
    ChatDisabledError,
    ChatGenerationConflictError,
    ChatGlobalConcurrencyError,
    ChatRateLimitError,
    ChatRegenerationConflictError,
    ChatUserConcurrencyError,
)

CHAT_HTTP_ERRORS = {
    ChatConversationNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        'Conversation not found.',
    ),
    ChatConversationBusyError: (
        status.HTTP_409_CONFLICT,
        'Conversation has an active generation.',
    ),
    ChatGenerationConflictError: (
        status.HTTP_409_CONFLICT,
        'Generation is no longer active.',
    ),
    ChatRegenerationConflictError: (
        status.HTTP_409_CONFLICT,
        'The selected message cannot be regenerated.',
    ),
    ChatDailyLimitError: (
        status.HTTP_429_TOO_MANY_REQUESTS,
        'Daily chat limit reached.',
    ),
    ChatRateLimitError: (
        status.HTTP_429_TOO_MANY_REQUESTS,
        'Chat rate limit reached.',
    ),
    ChatUserConcurrencyError: (
        status.HTTP_429_TOO_MANY_REQUESTS,
        'User generation limit reached.',
    ),
    ChatGlobalConcurrencyError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        'Chat generation capacity reached.',
    ),
    ChatDisabledError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        'Chat assistant is disabled.',
    ),
}

CHAT_DOMAIN_ERRORS = tuple(CHAT_HTTP_ERRORS)


def chat_http_exception(error: Exception) -> HTTPException:
    """Convert a known chat domain error into a safe HTTP error."""

    status_code, detail = CHAT_HTTP_ERRORS.get(
        type(error),
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            'Internal chat error.',
        ),
    )

    return HTTPException(
        status_code=status_code,
        detail=detail,
    )
