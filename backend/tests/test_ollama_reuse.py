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
    ProviderFinishReason,
    ProviderMessage,
    ProviderRequest,
    ProviderRole,
    ProviderUsage,
)
from app.services.providers.exceptions import ProviderError


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_REUSE_TEST_',
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
                content='Mensagem de teste',
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

    return (json.dumps(data) + '\n').encode()


class StrictByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    @override
    async def __aiter__(self):
        assert not self.closed

        for chunk in self.chunks:
            yield chunk

    @override
    async def aclose(self):
        self.closed = True


class StrictTransport(httpx.AsyncBaseTransport):
    def __init__(self, body, *, status=200):
        self.body = body
        self.status = status
        self.closed = False
        self.requests = []

    @override
    async def handle_async_request(self, request):
        assert not self.closed, 'Closed transport reused.'

        self.requests.append(request)

        return httpx.Response(
            self.status,
            headers={
                'content-type': 'application/x-ndjson',
            },
            stream=self.body,
        )

    @override
    async def aclose(self):
        self.closed = True


def install_transports(monkeypatch, transports):
    original_client = httpx.AsyncClient
    remaining = iter(transports)
    clients = []

    def create_client(*args, **kwargs):
        assert kwargs.get('transport') is None

        kwargs['transport'] = next(remaining)

        client = original_client(*args, **kwargs)
        clients.append(client)

        return client

    monkeypatch.setattr(httpx, 'AsyncClient', create_client)

    return clients


async def collect_events(provider, request):
    return [event async for event in provider.stream(request)]


def expected_events(content):
    return [
        ProviderDelta(content=content),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        ),
    ]


async def test_same_provider_consecutive_generations(
    settings,
    provider_request,
    monkeypatch,
):
    first = StrictTransport(
        StrictByteStream([
            make_event('Primeira resposta', done=True),
        ]),
    )

    second = StrictTransport(
        StrictByteStream([
            make_event('Segunda resposta', done=True),
        ]),
    )

    clients = install_transports(
        monkeypatch,
        [first, second],
    )

    provider = OllamaProvider(settings)

    assert await collect_events(
        provider,
        provider_request,
    ) == expected_events('Primeira resposta')

    assert first.closed is True
    assert first.body.closed is True

    assert await collect_events(
        provider,
        provider_request,
    ) == expected_events('Segunda resposta')

    assert second.closed is True
    assert second.body.closed is True

    assert len(clients) == 2
    assert clients[0] is not clients[1]
    assert all(client.is_closed for client in clients)

    assert len(first.requests) == 1
    assert len(second.requests) == 1


@pytest.mark.parametrize(
    ('status', 'chunks', 'error_code'),
    [
        (
            503,
            [b'Unavailable'],
            'PROVIDER_UNAVAILABLE',
        ),
        (
            200,
            [b'invalid-json\n'],
            'INVALID_PROVIDER_RESPONSE',
        ),
        (
            200,
            [make_event('Resposta incompleta')],
            'STREAM_INTERRUPTED',
        ),
    ],
    ids=['http-error', 'invalid-response', 'interrupted'],
)
async def test_same_provider_recovers_after_failure(
    settings,
    provider_request,
    monkeypatch,
    status,
    chunks,
    error_code,
):
    first = StrictTransport(
        StrictByteStream(chunks),
        status=status,
    )

    second = StrictTransport(
        StrictByteStream([
            make_event('Recuperado', done=True),
        ]),
    )

    clients = install_transports(
        monkeypatch,
        [first, second],
    )

    provider = OllamaProvider(settings)

    with pytest.raises(ProviderError, match=error_code):
        await collect_events(provider, provider_request)

    assert first.closed is True
    assert first.body.closed is True

    assert await collect_events(
        provider,
        provider_request,
    ) == expected_events('Recuperado')

    assert second.closed is True
    assert second.body.closed is True

    assert len(clients) == 2
    assert all(client.is_closed for client in clients)

    assert len(first.requests) == 1
    assert len(second.requests) == 1


async def test_same_provider_recovers_after_early_close(
    settings,
    provider_request,
    monkeypatch,
):
    first = StrictTransport(
        StrictByteStream([
            make_event('Resposta parcial'),
            make_event(done=True),
        ]),
    )

    second = StrictTransport(
        StrictByteStream([
            make_event('Nova resposta', done=True),
        ]),
    )

    clients = install_transports(
        monkeypatch,
        [first, second],
    )

    provider = OllamaProvider(settings)

    async with aclosing(provider.stream(provider_request)) as stream:
        assert await anext(stream) == ProviderDelta(
            content='Resposta parcial',
        )

    assert first.closed is True
    assert first.body.closed is True

    assert await collect_events(
        provider,
        provider_request,
    ) == expected_events('Nova resposta')

    assert second.closed is True
    assert second.body.closed is True

    assert len(clients) == 2
    assert all(client.is_closed for client in clients)


class BlockingByteStream(StrictByteStream):
    def __init__(self, chunks):
        super().__init__(chunks)
        self.waiting = asyncio.Event()
        self.release = asyncio.Event()

    @override
    async def __aiter__(self):
        async for chunk in super().__aiter__():
            yield chunk

        self.waiting.set()
        await self.release.wait()


class BrokenByteStream(StrictByteStream):
    @override
    async def __aiter__(self):
        async for chunk in super().__aiter__():
            yield chunk

        raise httpx.ReadError('Simulated read failure.')


@pytest.mark.parametrize(
    'chunks',
    [
        [],
        [make_event('Conteudo parcial')],
    ],
    ids=['before-content', 'after-content'],
)
async def test_same_provider_recovers_after_cancellation(
    settings,
    provider_request,
    monkeypatch,
    chunks,
):
    body = BlockingByteStream(chunks)
    first = StrictTransport(body)

    second = StrictTransport(
        StrictByteStream([
            make_event('Nova resposta', done=True),
        ]),
    )

    clients = install_transports(
        monkeypatch,
        [first, second],
    )

    provider = OllamaProvider(settings)
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
        assert len(received) == len(chunks)
        assert first.closed is True
        assert body.closed is True
        assert clients[0].is_closed is True

        assert await collect_events(
            provider,
            provider_request,
        ) == expected_events('Nova resposta')

        assert second.closed is True
        assert second.body.closed is True

        assert len(clients) == 2
        assert clients[0] is not clients[1]
        assert all(client.is_closed for client in clients)

        assert len(first.requests) == 1
        assert len(second.requests) == 1
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(
                task,
                return_exceptions=True,
            )


async def test_same_provider_resets_content_started(
    settings,
    provider_request,
    monkeypatch,
):
    first = StrictTransport(
        BrokenByteStream([
            make_event('Conteudo parcial'),
        ]),
    )

    second = StrictTransport(
        BrokenByteStream([]),
    )

    third = StrictTransport(
        StrictByteStream([
            make_event('Recuperado', done=True),
        ]),
    )

    clients = install_transports(
        monkeypatch,
        [first, second, third],
    )

    provider = OllamaProvider(settings)

    async with aclosing(provider.stream(provider_request)) as stream:
        assert await anext(stream) == ProviderDelta(
            content='Conteudo parcial',
        )

        with pytest.raises(
            ProviderError,
            match='STREAM_INTERRUPTED',
        ):
            await anext(stream)

    assert first.closed is True
    assert first.body.closed is True

    with pytest.raises(
        ProviderError,
        match='PROVIDER_UNAVAILABLE',
    ):
        await collect_events(
            provider,
            provider_request,
        )

    assert second.closed is True
    assert second.body.closed is True

    assert await collect_events(
        provider,
        provider_request,
    ) == expected_events('Recuperado')

    assert third.closed is True
    assert third.body.closed is True

    assert len(clients) == 3
    assert all(client.is_closed for client in clients)

    assert len(first.requests) == 1
    assert len(second.requests) == 1
    assert len(third.requests) == 1
