from enum import StrEnum


class ProviderErrorCode(StrEnum):
    MODEL_NOT_FOUND = 'MODEL_NOT_FOUND'
    PROVIDER_REQUEST_ERROR = 'PROVIDER_REQUEST_ERROR'
    PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE'
    GENERATION_TIMEOUT = 'GENERATION_TIMEOUT'
    INVALID_PROVIDER_RESPONSE = 'INVALID_PROVIDER_RESPONSE'
    STREAM_INTERRUPTED = 'STREAM_INTERRUPTED'


class ProviderError(Exception):
    """Sanitized error raised by an AI provider."""

    def __init__(self, code: ProviderErrorCode) -> None:
        self.code = code
        super().__init__(code.value)
