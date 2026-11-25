from app.services.providers.base import (
    ProviderCompletion,
    ProviderDelta,
    ProviderEvent,
    ProviderFinishReason,
    ProviderUsage,
)
from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)

MAX_PROVIDER_TOKEN_COUNT = 2_147_483_647


def _validate_content_encoding(content: str) -> None:
    try:
        content.encode('utf-8')
    except UnicodeEncodeError:
        raise ProviderError(
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE
        ) from None


def _validate_intermediate_event(
    data: dict[str, object],
) -> None:
    terminal_fields = {
        'done_reason',
        'prompt_eval_count',
        'eval_count',
    }

    if terminal_fields.intersection(data):
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def _validate_provider_error(
    data: dict[str, object],
) -> None:
    error = data['error']

    if not isinstance(error, str) or not error.strip():
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    raise ProviderError(ProviderErrorCode.PROVIDER_REQUEST_ERROR)


def _extract_content(data: dict[str, object]) -> str:
    message = data.get('message')

    if not isinstance(message, dict):
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    if message.get('role') != 'assistant':
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    if 'tool_calls' in message:
        if message['tool_calls'] != []:
            raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    content = message.get('content')

    if not isinstance(content, str) or chr(0) in content:
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    _validate_content_encoding(content)

    return content


def _extract_token_count(
    data: dict[str, object],
    field: str,
) -> int | None:
    if field not in data:
        return None

    value = data[field]

    if type(value) is not int or not 0 <= value <= MAX_PROVIDER_TOKEN_COUNT:
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    return value


def _build_completion(
    data: dict[str, object],
) -> ProviderCompletion:
    try:
        finish_reason = ProviderFinishReason(data.get('done_reason'))
    except (ValueError, TypeError):
        raise ProviderError(
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE
        ) from None

    usage = ProviderUsage(
        input_tokens=_extract_token_count(data, 'prompt_eval_count'),
        output_tokens=_extract_token_count(data, 'eval_count'),
    )

    return ProviderCompletion(
        finish_reason=finish_reason,
        usage=usage,
    )


def _validate_model_identity(
    data: dict[str, object],
    expected_model: str,
) -> None:
    model = data.get('model')

    if not isinstance(model, str) or model != expected_model:
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def parse_ollama_event(
    data: dict[str, object],
    *,
    expected_model: str,
) -> tuple[ProviderEvent, ...]:
    """Convert an Ollama response into provider events."""

    if 'error' in data:
        _validate_provider_error(data)

    _validate_model_identity(data, expected_model)

    done = data.get('done')

    if type(done) is not bool:
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    if not done:
        _validate_intermediate_event(data)

    content = _extract_content(data)

    events: list[ProviderEvent] = []

    if content:
        events.append(ProviderDelta(content=content))

    if done:
        events.append(_build_completion(data))

    return tuple(events)
