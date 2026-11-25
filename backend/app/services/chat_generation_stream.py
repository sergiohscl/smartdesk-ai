import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from dataclasses import dataclass, field

from anyio import CancelScope

from app.models.chat_message import ChatMessageStatus
from app.schemas.chat import ChatStreamErrorCode
from app.services.chat_errors import map_chat_error
from app.services.providers.base import (
    AIProvider,
    ProviderCompletion,
    ProviderDelta,
    ProviderEvent,
    ProviderFinishReason,
    ProviderRequest,
    ProviderUsage,
)
from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)

MAX_TOKEN_COUNT = 2_147_483_647
MAX_RESPONSE_BYTES = 1024 * 1024


@dataclass(slots=True)
class GenerationResult:
    chunks: list[str] = field(default_factory=list)
    status: ChatMessageStatus = ChatMessageStatus.FAILED
    usage: ProviderUsage = field(default_factory=ProviderUsage)
    error_code: ChatStreamErrorCode | None = None
    received_bytes: int = 0

    @property
    def content(self) -> str:
        return ''.join(self.chunks)

    def append(self, content: str) -> None:
        size = len(content.encode('utf-8'))

        if self.received_bytes + size > MAX_RESPONSE_BYTES:
            raise ProviderError(
                ProviderErrorCode.INVALID_PROVIDER_RESPONSE,
            )

        self.chunks.append(content)
        self.received_bytes += size

    def complete(self, event: ProviderCompletion) -> None:
        for count in (
            event.usage.input_tokens,
            event.usage.output_tokens,
        ):
            if count is not None and count > MAX_TOKEN_COUNT:
                raise ProviderError(
                    ProviderErrorCode.INVALID_PROVIDER_RESPONSE,
                )

        if (
            event.finish_reason == ProviderFinishReason.STOP
            and not self.content.strip()
        ):
            raise ProviderError(
                ProviderErrorCode.INVALID_PROVIDER_RESPONSE,
            )

        self.usage = event.usage
        self.status = (
            ChatMessageStatus.TRUNCATED
            if event.finish_reason == ProviderFinishReason.LENGTH
            else ChatMessageStatus.COMPLETED
        )

    def cancel(self) -> None:
        self.status = ChatMessageStatus.CANCELLED
        self.error_code = None

    def fail(self, error: Exception) -> None:
        self.status = ChatMessageStatus.FAILED
        self.error_code = map_chat_error(error)


CANCELLATION_POLL_SECONDS = 0.5


class GenerationCancelled(Exception):
    """Generation cancellation was requested."""


async def _next_event(
    events: AsyncIterator[ProviderEvent],
    cancellation_check: Callable[[], Awaitable[bool]] | None,
) -> ProviderEvent | None:
    if cancellation_check is None:
        return await anext(events, None)

    if await cancellation_check():
        raise GenerationCancelled

    task = asyncio.ensure_future(anext(events, None))

    try:
        while True:
            done, _ = await asyncio.wait(
                {task},
                timeout=CANCELLATION_POLL_SECONDS,
            )

            if done:
                return task.result()

            if await cancellation_check():
                raise GenerationCancelled
    finally:
        if not task.done():
            task.cancel()

        with CancelScope(shield=True):
            await asyncio.gather(task, return_exceptions=True)


async def _consume_events(
    *,
    provider: AIProvider,
    request: ProviderRequest,
    result: GenerationResult,
    deadline: float,
    cancellation_check: Callable[[], Awaitable[bool]] | None,
) -> AsyncIterator[str]:
    async with aclosing(provider.stream(request)) as events:
        while True:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError

            async with asyncio.timeout_at(deadline):
                event = await _next_event(
                    events,
                    cancellation_check,
                )

            if event is None:
                raise ProviderError(
                    ProviderErrorCode.STREAM_INTERRUPTED,
                )

            if isinstance(event, ProviderDelta):
                result.append(event.content)
                yield event.content
            elif isinstance(event, ProviderCompletion):
                result.complete(event)
                return
            else:
                raise ProviderError(
                    ProviderErrorCode.INVALID_PROVIDER_RESPONSE,
                )


async def consume_generation(
    *,
    provider: AIProvider,
    request: ProviderRequest,
    result: GenerationResult,
    timeout_seconds: float,
    cancellation_check: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[str]:
    """Consume provider events within an absolute deadline."""

    deadline = asyncio.get_running_loop().time() + timeout_seconds

    try:
        async with aclosing(
            _consume_events(
                provider=provider,
                request=request,
                result=result,
                deadline=deadline,
                cancellation_check=cancellation_check,
            ),
        ) as events:
            async for content in events:
                yield content
    except GenerationCancelled:
        result.cancel()
    except Exception as error:
        result.fail(error)
