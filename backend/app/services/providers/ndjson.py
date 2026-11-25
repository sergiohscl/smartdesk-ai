import json
from typing import NoReturn

from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)

MAX_JSON_DEPTH = 32
MAX_NDJSON_LINE_BYTES = 256 * 1024


def _validate_line_size(line: str) -> None:
    if len(line) > MAX_NDJSON_LINE_BYTES:
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    try:
        size = len(line.encode('utf-8'))
    except UnicodeEncodeError:
        raise ProviderError(
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE
        ) from None

    if size > MAX_NDJSON_LINE_BYTES:
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in pairs:
        if key in result:
            raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

        result[key] = value

    return result


def _validate_json_depth(line: str) -> None:
    """Reject excessive nesting before JSON decoding."""

    depth = 0
    in_string = False
    escaped = False

    for char in line:
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False

            continue

        if char == '"':
            in_string = True
        elif char in '{[':
            depth += 1

            if depth > MAX_JSON_DEPTH:
                raise ProviderError(
                    ProviderErrorCode.INVALID_PROVIDER_RESPONSE
                )
        elif char in '}]':
            depth -= 1

            if depth < 0:
                raise ProviderError(
                    ProviderErrorCode.INVALID_PROVIDER_RESPONSE
                )


def _reject_constant(value: str) -> NoReturn:
    raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


def parse_ndjson_line(
    line: str,
) -> dict[str, object] | None:
    """Decode one NDJSON line without exposing raw errors."""

    _validate_line_size(line)

    if not line.strip():
        return None

    _validate_json_depth(line)

    try:
        data = json.loads(
            line,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (ValueError, RecursionError):
        raise ProviderError(
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE
        ) from None

    if not isinstance(data, dict):
        raise ProviderError(ProviderErrorCode.INVALID_PROVIDER_RESPONSE)

    return data
