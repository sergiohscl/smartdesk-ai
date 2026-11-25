from collections.abc import (
    AsyncGenerator,
    Awaitable,
    Callable,
)
from contextlib import aclosing

from anyio import CancelScope
from fastapi.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from app.schemas.chat import ChatStreamEvent

CleanupCallback = Callable[[], Awaitable[None]]


def encode_sse_event(event: ChatStreamEvent) -> bytes:
    """Serialize a typed chat event using the SSE wire format."""

    payload = event.model_dump_json()

    return (f'event: {event.type}\ndata: {payload}\n\n').encode('utf-8')


async def stream_sse_events(
    events: AsyncGenerator[ChatStreamEvent, None],
) -> AsyncGenerator[bytes, None]:
    """Convert chat events into SSE frames."""

    async with aclosing(events):
        async for event in events:
            yield encode_sse_event(event)


class ChatStreamingResponse(StreamingResponse):
    """Manage the lifecycle of chat event generators."""

    def __init__(
        self,
        events: AsyncGenerator[ChatStreamEvent, None],
        *,
        on_unstarted: CleanupCallback | None = None,
    ) -> None:
        self._events = events
        self._started = False
        self._on_unstarted = on_unstarted
        self._frames = self._iterate_frames()

        super().__init__(
            self._frames,
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-store',
                'X-Accel-Buffering': 'no',
            },
        )

    async def _iterate_frames(
        self,
    ) -> AsyncGenerator[bytes, None]:
        self._started = True

        async with aclosing(
            stream_sse_events(self._events),
        ) as frames:
            async for frame in frames:
                yield frame

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        try:
            await super().__call__(
                scope,
                receive,
                send,
            )
        finally:
            with CancelScope(shield=True):
                try:
                    await self._frames.aclose()
                finally:
                    try:
                        await self._events.aclose()
                    finally:
                        if (
                            not self._started
                            and self._on_unstarted is not None
                        ):
                            await self._on_unstarted()


def create_sse_response(
    events: AsyncGenerator[ChatStreamEvent, None],
    *,
    on_unstarted: CleanupCallback | None = None,
) -> StreamingResponse:
    """Build a streaming HTTP response for chat events."""

    return ChatStreamingResponse(
        events,
        on_unstarted=on_unstarted,
    )
