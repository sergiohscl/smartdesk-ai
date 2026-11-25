import httpx
import pytest

from app.services.providers.exceptions import ProviderErrorCode
from app.services.providers.ollama_errors import classify_httpx_error


@pytest.mark.parametrize(
    'error_type',
    [
        httpx.TimeoutException,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    ],
)
@pytest.mark.parametrize('content_started', [False, True])
def test_ollama_errors_classifies_timeout(
    error_type,
    content_started,
):
    error = error_type('Simulated timeout.')

    assert (
        classify_httpx_error(
            error,
            content_started=content_started,
        )
        == ProviderErrorCode.GENERATION_TIMEOUT
    )


@pytest.mark.parametrize(
    'error_type',
    [
        httpx.RequestError,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.WriteError,
        httpx.CloseError,
        httpx.RemoteProtocolError,
        httpx.LocalProtocolError,
        httpx.ProxyError,
    ],
)
def test_ollama_errors_before_content(error_type):
    error = error_type('Simulated transport failure.')

    assert (
        classify_httpx_error(
            error,
            content_started=False,
        )
        == ProviderErrorCode.PROVIDER_UNAVAILABLE
    )


@pytest.mark.parametrize(
    'error_type',
    [
        httpx.RequestError,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.WriteError,
        httpx.CloseError,
        httpx.RemoteProtocolError,
        httpx.LocalProtocolError,
        httpx.ProxyError,
    ],
)
def test_ollama_errors_after_content(error_type):
    error = error_type('Simulated transport failure.')

    assert (
        classify_httpx_error(
            error,
            content_started=True,
        )
        == ProviderErrorCode.STREAM_INTERRUPTED
    )


@pytest.mark.parametrize('content_started', [False, True])
def test_ollama_errors_classifies_decoding_error(
    content_started,
):
    error = httpx.DecodingError('Simulated decoding failure.')

    assert (
        classify_httpx_error(
            error,
            content_started=content_started,
        )
        == ProviderErrorCode.INVALID_PROVIDER_RESPONSE
    )
