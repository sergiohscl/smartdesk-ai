from typing import override

import httpx
import pytest

from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)
from app.services.providers.ollama_http import (
    validate_ollama_response,
)


@pytest.mark.parametrize(
    ('status_code', 'expected_code'),
    [
        (100, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (101, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (201, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (202, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (204, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (206, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (299, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (301, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (302, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (304, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (307, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (308, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (400, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (401, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (403, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (404, ProviderErrorCode.MODEL_NOT_FOUND),
        (405, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (408, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (409, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (413, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (422, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (429, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (499, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (500, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (501, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (502, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (503, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (504, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (599, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (600, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
    ],
)
def test_ollama_http_rejects_status(
    status_code,
    expected_code,
):
    response = httpx.Response(status_code)

    with pytest.raises(
        ProviderError,
        match=expected_code.value,
    ) as exc_info:
        validate_ollama_response(response)

    assert exc_info.value.code == expected_code


@pytest.mark.parametrize(
    'content_type',
    [
        'application/x-ndjson',
        'Application/X-NDJSON',
        'application/x-ndjson; charset=utf-8',
        'application/x-ndjson; charset=UTF-8',
        ' application/x-ndjson ',
    ],
)
def test_ollama_http_accepts_content_type(content_type):
    response = httpx.Response(
        200,
        headers={'content-type': content_type},
    )

    assert validate_ollama_response(response) is None


@pytest.mark.parametrize(
    'content_type',
    [
        None,
        '',
        'application/json',
        'text/html',
        'text/plain',
        'application/octet-stream',
        'text/event-stream',
        'application/x-ndjson-invalid',
        'application/x-ndjson, application/json',
    ],
)
def test_ollama_http_rejects_content_type(content_type):
    headers = {}

    if content_type is not None:
        headers['content-type'] = content_type

    response = httpx.Response(
        200,
        headers=headers,
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        validate_ollama_response(response)


@pytest.mark.parametrize(
    'encoding',
    [
        None,
        'identity',
        'Identity',
        ' identity ',
    ],
)
def test_ollama_http_accepts_identity_encoding(encoding):
    headers = {
        'content-type': 'application/x-ndjson',
    }

    if encoding is not None:
        headers['content-encoding'] = encoding

    response = httpx.Response(
        200,
        headers=headers,
    )

    assert validate_ollama_response(response) is None


@pytest.mark.parametrize(
    'encoding',
    [
        '',
        'gzip',
        'deflate',
        'br',
        'zstd',
        'gzip, br',
        'identity, gzip',
        'unknown',
    ],
)
def test_ollama_http_rejects_encoding(encoding):
    response = httpx.Response(
        200,
        headers={
            'content-type': 'application/x-ndjson',
            'content-encoding': encoding,
        },
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        validate_ollama_response(response)


def test_ollama_http_validates_status_before_headers():
    response = httpx.Response(
        404,
        headers={
            'content-type': 'text/html',
            'content-encoding': 'gzip',
        },
    )

    with pytest.raises(
        ProviderError,
        match='MODEL_NOT_FOUND',
    ):
        validate_ollama_response(response)


def test_ollama_http_sanitizes_error():
    secret = 'fake-sensitive-provider-error'

    response = httpx.Response(
        500,
        json={'error': secret},
    )

    with pytest.raises(
        ProviderError,
        match='PROVIDER_UNAVAILABLE',
    ) as exc_info:
        validate_ollama_response(response)

    assert secret not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


class UnreadableStream(httpx.AsyncByteStream):
    @override
    async def __aiter__(self):
        raise AssertionError('Response body must not be consumed.')
        yield b''


@pytest.mark.parametrize(
    'status_code',
    [200, 400, 404, 500],
)
async def test_ollama_http_does_not_consume_body(status_code):
    response = httpx.Response(
        status_code,
        headers={
            'content-type': 'application/x-ndjson',
        },
        stream=UnreadableStream(),
    )

    try:
        if status_code == 200:
            validate_ollama_response(response)
        else:
            with pytest.raises(
                ProviderError,
                match='MODEL_NOT_FOUND|PROVIDER_REQUEST_ERROR|'
                'PROVIDER_UNAVAILABLE',
            ):
                validate_ollama_response(response)

        assert response.is_stream_consumed is False
    finally:
        await response.aclose()
