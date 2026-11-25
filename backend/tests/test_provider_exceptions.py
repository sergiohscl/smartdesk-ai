import pytest

from app.services.providers import (
    ProviderError,
    ProviderErrorCode,
)


def test_provider_error_code_values():
    assert {code.value for code in ProviderErrorCode} == {
        'MODEL_NOT_FOUND',
        'PROVIDER_REQUEST_ERROR',
        'PROVIDER_UNAVAILABLE',
        'GENERATION_TIMEOUT',
        'INVALID_PROVIDER_RESPONSE',
        'STREAM_INTERRUPTED',
    }


@pytest.mark.parametrize('code', list(ProviderErrorCode))
def test_provider_error_preserves_code(code):
    error = ProviderError(code)

    assert error.code is code
    assert str(error) == code.value
    assert isinstance(error, Exception)


def test_provider_error_can_be_caught():
    with pytest.raises(
        ProviderError,
        match='PROVIDER_UNAVAILABLE',
    ) as exc_info:
        raise ProviderError(ProviderErrorCode.PROVIDER_UNAVAILABLE)

    assert exc_info.value.code is (ProviderErrorCode.PROVIDER_UNAVAILABLE)
