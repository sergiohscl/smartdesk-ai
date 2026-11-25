import asyncio
import json
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import ClientDisconnect

from app.api.v1.chat_sse import (
    create_sse_response,
    encode_sse_event,
    stream_sse_events,
)
from app.schemas.chat import (
    ChatMessageCreatedEvent,
    ChatResponseDeltaEvent,
)

GENERATION_ID = UUID(
    '123e4567-e89b-12d3-a456-426614174000',
)


def make_delta(content: str) -> ChatResponseDeltaEvent:
    return ChatResponseDeltaEvent(
        type='response.delta',
        conversation_id=10,
        generation_id=GENERATION_ID,
        assistant_message_id=21,
        delta=content,
    )


def test_encode_message_created_event():
    event = ChatMessageCreatedEvent(
        type='message.created',
        conversation_id=10,
        generation_id=GENERATION_ID,
        assistant_message_id=21,
        user_message_id=20,
    )

    frame = encode_sse_event(event).decode('utf-8')

    assert frame.startswith('event: message.created\n')
    assert frame.endswith('\n\n')

    data = frame.splitlines()[1].removeprefix('data: ')

    assert json.loads(data) == event.model_dump(
        mode='json',
    )


@pytest.mark.parametrize(
    'content',
    [
        'Olá, como posso ajudar?',
        'Linha 1\nLinha 2',
        'Configuração: PostgreSQL',
        'Texto com emoji 🚀',
        'event: response.completed\n\ndata: falso',
    ],
)
def test_encode_delta_event(content):
    event = make_delta(content)

    frame = encode_sse_event(event).decode('utf-8')

    assert frame.startswith('event: response.delta\n')
    assert frame.endswith('\n\n')
    assert len(frame.splitlines()) == 3

    data = frame.splitlines()[1].removeprefix('data: ')

    assert json.loads(data)['delta'] == content


async def test_stream_sse_events_preserves_order():
    async def events():
        yield make_delta('Primeiro')
        yield make_delta('Segundo')

    frames = [frame async for frame in stream_sse_events(events())]

    assert frames == [
        encode_sse_event(make_delta('Primeiro')),
        encode_sse_event(make_delta('Segundo')),
    ]


async def test_stream_sse_events_closes_source():
    closed = False

    async def events():
        nonlocal closed

        try:
            yield make_delta('Primeiro')
            yield make_delta('Segundo')
        finally:
            closed = True

    stream = stream_sse_events(events())

    try:
        first = await anext(stream)

        assert first == encode_sse_event(
            make_delta('Primeiro'),
        )
        assert not closed
    finally:
        await stream.aclose()

    assert closed


async def test_create_sse_response():
    async def events():
        yield make_delta('Resposta')

    response = create_sse_response(events())

    assert response.status_code == 200
    assert response.headers['content-type'].startswith(
        'text/event-stream',
    )
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-accel-buffering'] == 'no'
    assert 'content-length' not in response.headers

    frames = [frame async for frame in response.body_iterator]

    assert frames == [
        encode_sse_event(make_delta('Resposta')),
    ]


async def test_sse_send_failure_closes_source():
    closed = False

    async def events():
        nonlocal closed

        try:
            yield make_delta('Primeiro')
            yield make_delta('Segundo')
        finally:
            closed = True

    async def receive():
        return {'type': 'http.disconnect'}

    async def send(message):
        if message['type'] == 'http.response.body':
            raise OSError('Connection closed.')

    response = create_sse_response(events())

    scope = {
        'type': 'http',
        'asgi': {
            'version': '3.0',
            'spec_version': '2.4',
        },
    }

    with pytest.raises(ClientDisconnect):
        await response(scope, receive, send)

    assert closed


async def test_sse_normal_completion_closes_source():
    closed = False
    messages = []

    async def events():
        nonlocal closed

        try:
            yield make_delta('Resposta')
        finally:
            closed = True

    async def receive():
        return {'type': 'http.disconnect'}

    async def send(message):
        messages.append(message)

    response = create_sse_response(events())

    scope = {
        'type': 'http',
        'asgi': {
            'version': '3.0',
            'spec_version': '2.4',
        },
    }

    await response(scope, receive, send)

    assert closed
    assert messages[0]['type'] == 'http.response.start'
    assert messages[0]['status'] == 200

    assert messages[1]['body'] == encode_sse_event(
        make_delta('Resposta'),
    )

    assert messages[-1]['more_body'] is False


async def test_sse_disconnect_before_first_event():
    started = False
    cleanup_calls = 0

    async def events():
        nonlocal started

        started = True
        yield make_delta('Resposta')

    async def cleanup():
        nonlocal cleanup_calls

        cleanup_calls += 1

    async def receive():
        return {'type': 'http.disconnect'}

    async def send(message):
        if message['type'] == 'http.response.start':
            raise OSError('Connection closed.')

    response = create_sse_response(
        events(),
        on_unstarted=cleanup,
    )

    scope = {
        'type': 'http',
        'asgi': {
            'version': '3.0',
            'spec_version': '2.4',
        },
    }

    with pytest.raises(ClientDisconnect):
        await response(scope, receive, send)

    assert started is False
    assert cleanup_calls == 1


async def test_sse_dependency_lifecycle():
    application = FastAPI()
    lifecycle = []

    async def session_dependency():
        lifecycle.append('session.open')

        try:
            yield object()
        finally:
            lifecycle.append('session.close')

    @application.get('/stream')
    async def endpoint(
        session: Annotated[
            object,
            Depends(session_dependency),
        ],
    ):
        assert session is not None

        lifecycle.append('endpoint')

        async def events():
            assert 'session.close' not in lifecycle

            lifecycle.append('stream.start')

            try:
                yield make_delta('Resposta')

                assert 'session.close' not in lifecycle
            finally:
                lifecycle.append('stream.close')

        return create_sse_response(events())

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url='http://test',
    ) as client:
        response = await client.get('/stream')

    assert response.status_code == 200

    assert lifecycle == [
        'session.open',
        'endpoint',
        'stream.start',
        'stream.close',
        'session.close',
    ]


async def test_sse_asgi_23_disconnect():
    started = asyncio.Event()
    closed = asyncio.Event()

    async def events():
        try:
            started.set()

            yield make_delta('Resposta parcial')

            await asyncio.Event().wait()
        finally:
            closed.set()

    async def receive():
        await started.wait()

        return {'type': 'http.disconnect'}

    async def send(message):
        assert message['type'] in {
            'http.response.start',
            'http.response.body',
        }

    response = create_sse_response(events())

    scope = {
        'type': 'http',
        'asgi': {
            'version': '3.0',
            'spec_version': '2.3',
        },
    }

    await asyncio.wait_for(
        response(scope, receive, send),
        timeout=2,
    )

    assert closed.is_set()
