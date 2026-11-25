from collections.abc import AsyncIterable, AsyncIterator

from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)

MAX_NDJSON_LINE_BYTES = 256 * 1024


def _decode_line(buffer: bytearray) -> str:
    try:
        return buffer.decode('utf-8')
    except UnicodeDecodeError:
        raise ProviderError(
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE
        ) from None


async def iter_ndjson_lines(
    chunks: AsyncIterable[bytes],
) -> AsyncIterator[str]:
    """Read bounded UTF-8 lines from an asynchronous byte stream."""

    buffer = bytearray()

    async for chunk in chunks:
        start = 0

        while start < len(chunk):
            newline = chunk.find(b'\n', start)
            end = len(chunk) if newline == -1 else newline

            if len(buffer) + end - start > MAX_NDJSON_LINE_BYTES:
                raise ProviderError(
                    ProviderErrorCode.INVALID_PROVIDER_RESPONSE
                )

            buffer.extend(memoryview(chunk)[start:end])

            if newline == -1:
                break

            line = _decode_line(buffer)
            buffer.clear()

            yield line.removesuffix('\r')

            start = newline + 1

    if buffer:
        yield _decode_line(buffer).removesuffix('\r')
