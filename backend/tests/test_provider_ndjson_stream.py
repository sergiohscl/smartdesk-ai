import pytest

from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)
from app.services.providers.ndjson_stream import (
    MAX_NDJSON_LINE_BYTES,
    iter_ndjson_lines,
)


async def make_chunks(chunks):
    for chunk in chunks:
        yield chunk


async def collect_lines(chunks):
    return [line async for line in iter_ndjson_lines(make_chunks(chunks))]


@pytest.mark.parametrize(
    ('chunks', 'expected'),
    [
        ([], []),
        ([b''], []),
        ([b'hello\n'], ['hello']),
        ([b'hello'], ['hello']),
        ([b'hello\nworld\n'], ['hello', 'world']),
        ([b'hel', b'lo\n'], ['hello']),
        ([b'hello\nwor', b'ld\n'], ['hello', 'world']),
        ([b'hello', b'\n', b'world'], ['hello', 'world']),
        ([b'\n'], ['']),
        ([b'\n\n'], ['', '']),
        ([b'a\n\nb\n'], ['a', '', 'b']),
        ([b'a\r\nb\r\n'], ['a', 'b']),
        ([b'a\r', b'\n'], ['a']),
        ([b'a', b'', b'\n'], ['a']),
        ([b'  hello  \n'], ['  hello  ']),
        ([b'a\nb'], ['a', 'b']),
        ([b'a\n', b'b\n', b'c'], ['a', 'b', 'c']),
        ([b'{"done":true}\n'], ['{"done":true}']),
    ],
)
async def test_ndjson_stream_line_boundaries(chunks, expected):
    assert await collect_lines(chunks) == expected


@pytest.mark.parametrize(
    'content',
    [
        'Olá, usuário!',
        'Configuração',
        '🚀',
        '日本語',
        'Olá 🚀 日本語',
    ],
)
async def test_ndjson_stream_fragmented_utf8(content):
    encoded = (content + '\n').encode('utf-8')

    chunks = [bytes([value]) for value in encoded]

    assert await collect_lines(chunks) == [content]


@pytest.mark.parametrize(
    'chunks',
    [
        [b'\xff\n'],
        [b'\xfe\n'],
        [b'\xc3\n'],
        [b'\xf0\x9f\n'],
        [b'\xed\xa0\x80\n'],
        [b'\xc0\xaf\n'],
        [b'\xff'],
        [b'valid', b'\xff', b'\n'],
    ],
)
async def test_ndjson_stream_rejects_invalid_utf8(chunks):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        await collect_lines(chunks)

    assert exc_info.value.code == ProviderErrorCode.INVALID_PROVIDER_RESPONSE


@pytest.mark.parametrize(
    'size',
    [
        MAX_NDJSON_LINE_BYTES - 1,
        MAX_NDJSON_LINE_BYTES,
    ],
)
async def test_ndjson_stream_accepts_line_limit(size):
    content = b'a' * size

    assert await collect_lines([content, b'\n']) == ['a' * size]


@pytest.mark.parametrize(
    'chunks',
    [
        [b'a' * (MAX_NDJSON_LINE_BYTES + 1)],
        [b'a' * (MAX_NDJSON_LINE_BYTES + 1) + b'\n'],
        [b'a' * MAX_NDJSON_LINE_BYTES, b'b'],
        [b'a' * MAX_NDJSON_LINE_BYTES, b'b\n'],
        [
            b'a' * (MAX_NDJSON_LINE_BYTES // 2),
            b'b' * (MAX_NDJSON_LINE_BYTES // 2 + 1),
        ],
    ],
)
async def test_ndjson_stream_rejects_oversized_line(chunks):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        await collect_lines(chunks)


async def test_ndjson_stream_limit_is_per_line():
    content = b'a' * MAX_NDJSON_LINE_BYTES

    result = await collect_lines([content + b'\n' + content + b'\n'])

    assert result == [
        'a' * MAX_NDJSON_LINE_BYTES,
        'a' * MAX_NDJSON_LINE_BYTES,
    ]


async def test_ndjson_stream_limit_counts_bytes():
    content = 'é' * (MAX_NDJSON_LINE_BYTES // 2 + 1)

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        await collect_lines([content.encode('utf-8')])


async def test_ndjson_stream_yields_incrementally():
    consumed = []

    async def chunks():
        consumed.append(1)
        yield b'first\n'

        consumed.append(2)
        yield b'second\n'

    stream = iter_ndjson_lines(chunks())

    try:
        assert await anext(stream) == 'first'
        assert consumed == [1]

        assert await anext(stream) == 'second'
        assert consumed == [1, 2]

        with pytest.raises(StopAsyncIteration):
            await anext(stream)
    finally:
        await stream.aclose()


async def test_ndjson_stream_sanitizes_errors():
    secret = 'fake-sensitive-content'

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        await collect_lines([secret.encode('utf-8') + b'\xff\n'])

    assert secret not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


async def test_ndjson_stream_preserves_transport_error():
    async def chunks():
        yield b'first\n'
        raise ConnectionError('Simulated connection failure.')

    stream = iter_ndjson_lines(chunks())

    try:
        assert await anext(stream) == 'first'

        with pytest.raises(
            ConnectionError,
            match='Simulated connection failure',
        ):
            await anext(stream)
    finally:
        await stream.aclose()
