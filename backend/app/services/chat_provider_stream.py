import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing

from anyio import CancelScope

from app.services.providers.base import ProviderEvent

PROVIDER_CLOSE_TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)

_residual_tasks: set[asyncio.Task[None]] = set()


def _cleanup_finished(task: asyncio.Task[None]) -> None:
    _residual_tasks.discard(task)

    if task.cancelled():
        return

    if task.exception() is not None:
        logger.warning('Provider stream cleanup failed.')


class ProviderStream:
    """Manage provider iteration and bounded stream cleanup."""

    def __init__(
        self,
        events: AsyncIterator[ProviderEvent],
    ) -> None:
        self._events = events
        self._pending: asyncio.Future | None = None

    def next_event(self) -> asyncio.Future:
        """Start reading the next provider event."""

        self._pending = asyncio.ensure_future(
            anext(self._events, None),
        )

        return self._pending

    async def _close(self) -> None:
        if self._pending is not None:
            if not self._pending.done():
                self._pending.cancel()

            await asyncio.gather(
                self._pending,
                return_exceptions=True,
            )

        async with aclosing(self._events):
            pass

    async def close(self) -> None:
        """Close the stream without waiting indefinitely."""

        task = asyncio.create_task(self._close())

        _residual_tasks.add(task)
        task.add_done_callback(_cleanup_finished)

        with CancelScope(shield=True):
            done, _ = await asyncio.wait(
                {task},
                timeout=PROVIDER_CLOSE_TIMEOUT_SECONDS,
            )

        if not done:
            logger.warning(
                'Provider stream cleanup exceeded its deadline.',
            )
