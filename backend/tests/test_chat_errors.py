import pytest

from app.schemas.chat import ChatStreamErrorCode
from app.services.chat_errors import map_chat_error
from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)


@pytest.mark.parametrize('code', list(ProviderErrorCode))
def test_map_provider_error(code):
    error = ProviderError(code)

    assert map_chat_error(error) == ChatStreamErrorCode(
        code.value,
    )


def test_map_generation_timeout():
    error = TimeoutError('Generation deadline exceeded.')

    assert map_chat_error(error) == ChatStreamErrorCode.GENERATION_TIMEOUT


def test_map_unexpected_error():
    error = RuntimeError('fake-sensitive-internal-detail')

    assert map_chat_error(error) == ChatStreamErrorCode.INTERNAL_ERROR
