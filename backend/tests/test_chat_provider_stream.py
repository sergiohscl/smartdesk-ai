import asyncio

from anyio import CancelScope, create_task_group, fail_after

from app.services import chat_provider_stream
from app.services.chat_provider_stream import ProviderStream
from app.services.providers.base import ProviderDelta


async def test_provider_stream_cooperative_cleanup():
    started = asyncio.Event()
    closed = asyncio.Event()

    async def events():
        try:
            started.set()
            await asyncio.Event().wait()

            yield ProviderDelta(content='Resposta')
        finally:
            closed.set()

    stream = ProviderStream(events())
    task = stream.next_event()

    await asyncio.wait_for(started.wait(), timeout=1)

    await stream.close()

    assert task.done()
    assert closed.is_set()


async def test_provider_stream_non_cooperative_cleanup(
    monkeypatch,
):
    monkeypatch.setattr(
        chat_provider_stream,
        'PROVIDER_CLOSE_TIMEOUT_SECONDS',
        0.01,
    )

    started = asyncio.Event()
    release = asyncio.Event()
    closed = asyncio.Event()

    async def events():
        try:
            started.set()

            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await release.wait()

            yield ProviderDelta(content='Resposta tardia')
        finally:
            closed.set()

    stream = ProviderStream(events())
    task = stream.next_event()

    try:
        await asyncio.wait_for(
            started.wait(),
            timeout=1,
        )

        await asyncio.wait_for(
            stream.close(),
            timeout=1,
        )

        assert not task.done()
        assert not closed.is_set()
    finally:
        release.set()

        await asyncio.wait_for(
            closed.wait(),
            timeout=1,
        )

    assert task.done()
    assert closed.is_set()


async def test_finalization_shield_preserves_persistence():
    started = asyncio.Event()
    release = asyncio.Event()
    persisted = asyncio.Event()

    async def finalize():
        with fail_after(5, shield=True):
            started.set()
            await release.wait()
            persisted.set()

    with fail_after(2):
        async with create_task_group() as group:
            group.start_soon(finalize)

            await started.wait()

            group.cancel_scope.cancel()

            with CancelScope(shield=True):
                release.set()
                await persisted.wait()

    assert persisted.is_set()
