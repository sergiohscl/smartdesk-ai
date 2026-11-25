import httpx

from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)


def _validate_status(status_code: int) -> None:
    if status_code == 200:
        return

    if status_code == 404:
        raise ProviderError(ProviderErrorCode.MODEL_NOT_FOUND)

    if 400 <= status_code < 500:
        raise ProviderError(ProviderErrorCode.PROVIDER_REQUEST_ERROR)

    if 500 <= status_code < 600:
        raise ProviderError(ProviderErrorCode.PROVIDER_UNAVAILABLE)

    raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def _validate_content_type(headers: httpx.Headers) -> None:
    content_type = headers.get('content-type', '')
    media_type = content_type.partition(';')[0].strip().lower()

    if media_type != 'application/x-ndjson':
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def _validate_content_encoding(headers: httpx.Headers) -> None:
    encoding = (
        headers
        .get(
            'content-encoding',
            'identity',
        )
        .strip()
        .lower()
    )

    if encoding != 'identity':
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def validate_ollama_response(
    response: httpx.Response,
) -> None:
    """Validate HTTP metadata without consuming the response body."""

    _validate_status(response.status_code)
    _validate_content_type(response.headers)
    _validate_content_encoding(response.headers)
