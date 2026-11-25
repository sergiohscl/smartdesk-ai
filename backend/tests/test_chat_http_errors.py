import pytest

from app.api.v1.chat_http_errors import chat_http_exception
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


@pytest.mark.parametrize(
    ('error_type', 'expected_status'),
    [
        (ChatConversationNotFoundError, 404),
        (ChatConversationBusyError, 409),
        (ChatGenerationConflictError, 409),
        (ChatRegenerationConflictError, 409),
        (ChatDailyLimitError, 429),
        (ChatRateLimitError, 429),
        (ChatUserConcurrencyError, 429),
        (ChatGlobalConcurrencyError, 503),
        (ChatDisabledError, 503),
    ],
)
def test_chat_domain_error_mapping(
    error_type,
    expected_status,
):
    response = chat_http_exception(error_type())

    assert response.status_code == expected_status
    assert isinstance(response.detail, str)
    assert response.detail


def test_unknown_chat_error_does_not_expose_details():
    response = chat_http_exception(
        RuntimeError('Private internal information'),
    )

    assert response.status_code == 500
    assert response.detail == 'Internal chat error.'
