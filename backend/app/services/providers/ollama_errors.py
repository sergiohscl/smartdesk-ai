import httpx

from app.services.providers.exceptions import ProviderErrorCode


def classify_httpx_error(
    error: httpx.RequestError,
    *,
    content_started: bool,
) -> ProviderErrorCode:
    """Map HTTPX errors to sanitized provider error codes."""

    if isinstance(error, httpx.TimeoutException):
        return ProviderErrorCode.GENERATION_TIMEOUT

    if isinstance(error, httpx.DecodingError):
        return ProviderErrorCode.INVALID_PROVIDER_RESPONSE

    if content_started:
        return ProviderErrorCode.STREAM_INTERRUPTED

    return ProviderErrorCode.PROVIDER_UNAVAILABLE
