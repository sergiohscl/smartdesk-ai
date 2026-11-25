import asyncio
import json
from contextlib import aclosing
from typing import override

import httpx
import pytest
from pydantic_settings import SettingsConfigDict

from app.core.settings import Settings
from app.services.providers import (
    OllamaProvider,
    ProviderCompletion,
    ProviderDelta,
    ProviderMessage,
    ProviderRequest,
    ProviderRole,
)


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_LIFECYCLE_TEST_',
    )


@pytest.fixture
def settings():
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://test:test@localhost/test',
        JWT_SECRET_KEY='test-secret-not-for-production',
    )


@pytest.fixture
def provider_request():
    return ProviderRequest(
        messages=(
            ProviderMessage(
                role=ProviderRole.USER,
                content='Como configurar o PostgreSQL?',
            ),
        ),
    )


def make_event(content='', *, done=False):
    data = {
        'model': 'qwen2.5:7b',
        'message': {
            'role': 'assistant',
            'content': content,
        },
        'done': done,
    }

    if done:
        data['done_reason'] = 'stop'

    return (json.dumps(data) + '\n').encode('utf-8')


class TrackingByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks, *, block=False):
        self.chunks = chunks
        self.block = block
        self.closed = False
        self.read_count = 0
        self.waiting = asyncio.Event()
        self.release = asyncio.Event()

    @override
    async def __aiter__(self):
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk

        if self.block:
            self.waiting.set()
            await self.release.wait()

    @override
    async def aclose(self):
        self.closed = True
        self.release.set()


class TrackingTransport(httpx.MockTransport):
    def __init__(self, body):
        self.body = body
        self.requests = []
        self.closed = False

        super().__init__(self._handle_request)

    def _handle_request(self, request):
        self.requests.append(request)

        return httpx.Response(
            200,
            headers={
                'content-type': 'application/x-ndjson',
            },
            stream=self.body,
        )

    @override
    async def aclose(self):
        self.closed = True
        await super().aclose()


def make_provider(settings, chunks, *, block=False):
    body = TrackingByteStream(chunks, block=block)
    transport = TrackingTransport(body)

    provider = OllamaProvider(
        settings,
        transport=transport,
    )

    return provider, body, transport


async def test_stream_is_lazy(settings, provider_request):
    provider, body, transport = make_provider(
        settings,
        [make_event('Resposta', done=True)],
    )

    stream = provider.stream(provider_request)

    assert transport.requests == []
    assert body.read_count == 0

    await stream.aclose()

    assert transport.requests == []
    assert body.read_count == 0


async def test_stream_closes_after_completion(
    settings,
    provider_request,
):
    provider, body, transport = make_provider(
        settings,
        [
            make_event('Resposta'),
            make_event(done=True),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert len(events) == 2
    assert isinstance(events[-1], ProviderCompletion)
    assert body.closed is True
    assert transport.closed is True
    assert len(transport.requests) == 1


async def test_stream_explicit_close(
    settings,
    provider_request,
):
    provider, body, transport = make_provider(
        settings,
        [
            make_event('Primeiro fragmento'),
            make_event('Segundo fragmento'),
            make_event(done=True),
        ],
    )

    stream = provider.stream(provider_request)

    try:
        assert await anext(stream) == ProviderDelta(
            content='Primeiro fragmento',
        )
    finally:
        await stream.aclose()

    assert body.closed is True
    assert transport.closed is True
    assert body.read_count == 1
    assert len(transport.requests) == 1


async def test_stream_aclosing_on_early_break(
    settings,
    provider_request,
):
    provider, body, transport = make_provider(
        settings,
        [
            make_event('Primeiro fragmento'),
            make_event('Segundo fragmento'),
            make_event(done=True),
        ],
    )

    async with aclosing(provider.stream(provider_request)) as stream:
        async for event in stream:
            assert isinstance(event, ProviderDelta)
            break

    assert body.closed is True
    assert transport.closed is True
    assert body.read_count == 1


async def test_stream_close_is_idempotent(
    settings,
    provider_request,
):
    provider, body, transport = make_provider(
        settings,
        [make_event('Resposta parcial')],
    )

    stream = provider.stream(provider_request)

    try:
        await anext(stream)
    finally:
        await stream.aclose()

    await stream.aclose()

    assert body.closed is True
    assert transport.closed is True
    assert len(transport.requests) == 1


async def test_stream_close_after_terminal_event(
    settings,
    provider_request,
):
    provider, body, transport = make_provider(
        settings,
        [make_event(done=True)],
    )

    stream = provider.stream(provider_request)

    try:
        event = await anext(stream)
        assert isinstance(event, ProviderCompletion)
    finally:
        await stream.aclose()

    assert body.closed is True
    assert transport.closed is True


@pytest.mark.parametrize(
    'chunks',
    [
        [],
        [make_event('Resposta parcial')],
    ],
    ids=['before-content', 'after-content'],
)
async def test_stream_task_cancellation(
    settings,
    provider_request,
    chunks,
):
    provider, body, transport = make_provider(
        settings,
        chunks,
        block=True,
    )

    received = []

    async def consume():
        async with aclosing(provider.stream(provider_request)) as stream:
            async for event in stream:
                received.append(event)

    task = asyncio.create_task(consume())

    try:
        await asyncio.wait_for(
            body.waiting.wait(),
            timeout=2,
        )

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert task.cancelled() is True
        assert body.closed is True
        assert transport.closed is True
        assert len(received) == len(chunks)
        assert len(transport.requests) == 1
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(
                task,
                return_exceptions=True,
            )


async def test_new_stream_after_previous_close(
    settings,
    provider_request,
):
    first, first_body, first_transport = make_provider(
        settings,
        [make_event('Resposta interrompida')],
    )

    async with aclosing(first.stream(provider_request)) as stream:
        await anext(stream)

    second, second_body, second_transport = make_provider(
        settings,
        [make_event('Nova resposta', done=True)],
    )

    events = [event async for event in second.stream(provider_request)]

    assert len(events) == 2
    assert events[0] == ProviderDelta(
        content='Nova resposta',
    )
    assert isinstance(events[-1], ProviderCompletion)

    assert first_body.closed is True
    assert first_transport.closed is True
    assert second_body.closed is True
    assert second_transport.closed is True
