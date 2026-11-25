import json
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
from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_STREAM_TEST_',
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


class MockByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    @override
    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    @override
    async def aclose(self):
        self.closed = True


def make_event(content='', *, done=False, **extra):
    data = {
        'model': 'qwen2.5:7b',
        'message': {
            'role': 'assistant',
            'content': content,
        },
        'done': done,
    }

    data.update(extra)

    return (json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8')


def make_provider(settings, chunks, *, status=200):
    body = MockByteStream(chunks)
    requests = []

    def handler(request):
        requests.append(request)

        return httpx.Response(
            status,
            headers={
                'content-type': 'application/x-ndjson',
            },
            stream=body,
        )

    provider = OllamaProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    return provider, body, requests


async def test_ollama_stream_success(
    settings,
    provider_request,
):
    provider, body, requests = make_provider(
        settings,
        [
            make_event('Olá! '),
            make_event('Tudo bem?'),
            make_event(
                done=True,
                done_reason='stop',
                prompt_eval_count=25,
                eval_count=10,
            ),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert events == [
        ProviderDelta(content='Olá! '),
        ProviderDelta(content='Tudo bem?'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(
                input_tokens=25,
                output_tokens=10,
            ),
        ),
    ]

    assert body.closed is True
    assert len(requests) == 1


async def test_ollama_stream_http_request(
    settings,
    provider_request,
):
    provider, _, requests = make_provider(
        settings,
        [
            make_event(
                'Resposta',
                done=True,
                done_reason='stop',
            ),
        ],
    )

    _ = [event async for event in provider.stream(provider_request)]

    assert len(requests) == 1

    request = requests[0]
    payload = json.loads(request.content)

    assert request.method == 'POST'
    assert str(request.url) == 'http://ollama:11434/api/chat'
    assert request.headers['accept'] == 'application/x-ndjson'
    assert request.headers['accept-encoding'] == 'identity'
    assert 'authorization' not in request.headers
    assert payload['model'] == 'qwen2.5:7b'
    assert payload['stream'] is True


async def test_ollama_stream_fragmented_response(
    settings,
    provider_request,
):
    content = make_event('Olá 🚀') + make_event(
        done=True,
        done_reason='stop',
    )

    provider, _, _ = make_provider(
        settings,
        [bytes([value]) for value in content],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert events == [
        ProviderDelta(content='Olá 🚀'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        ),
    ]


async def test_ollama_stream_ignores_empty_lines(
    settings,
    provider_request,
):
    provider, _, _ = make_provider(
        settings,
        [
            b'\n',
            make_event('Resposta'),
            b'  \r\n',
            make_event(
                done=True,
                done_reason='stop',
            ),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert events == [
        ProviderDelta(content='Resposta'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        ),
    ]


async def test_ollama_stream_length_completion(
    settings,
    provider_request,
):
    provider, _, _ = make_provider(
        settings,
        [
            make_event(
                'Resposta parcial',
                done=True,
                done_reason='length',
                eval_count=768,
            ),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert events == [
        ProviderDelta(content='Resposta parcial'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.LENGTH,
            usage=ProviderUsage(output_tokens=768),
        ),
    ]


@pytest.mark.parametrize(
    'chunks',
    [
        [],
        [b'\n'],
        [make_event('Resposta incompleta')],
    ],
)
async def test_ollama_stream_requires_completion(
    settings,
    provider_request,
    chunks,
):
    provider, body, _ = make_provider(
        settings,
        chunks,
    )

    with pytest.raises(
        ProviderError,
        match='STREAM_INTERRUPTED',
    ) as exc_info:
        _ = [event async for event in provider.stream(provider_request)]

    assert exc_info.value.code == ProviderErrorCode.STREAM_INTERRUPTED
    assert body.closed is True


@pytest.mark.parametrize(
    ('status', 'code'),
    [
        (302, ProviderErrorCode.INVALID_PROVIDER_RESPONSE),
        (400, ProviderErrorCode.PROVIDER_REQUEST_ERROR),
        (404, ProviderErrorCode.MODEL_NOT_FOUND),
        (500, ProviderErrorCode.PROVIDER_UNAVAILABLE),
        (503, ProviderErrorCode.PROVIDER_UNAVAILABLE),
    ],
)
async def test_ollama_stream_http_errors(
    settings,
    provider_request,
    status,
    code,
):
    provider, body, requests = make_provider(
        settings,
        [b'fake-sensitive-error'],
        status=status,
    )

    with pytest.raises(
        ProviderError,
        match=code.value,
    ) as exc_info:
        _ = [event async for event in provider.stream(provider_request)]

    assert exc_info.value.code == code
    assert body.closed is True
    assert len(requests) == 1


@pytest.mark.parametrize(
    'chunk',
    [
        b'invalid-json\n',
        b'\xff\n',
        make_event('Resposta', model='qwen2.5:3b'),
        b'a' * (256 * 1024 + 1),
    ],
)
async def test_ollama_stream_invalid_response(
    settings,
    provider_request,
    chunk,
):
    provider, body, _ = make_provider(
        settings,
        [chunk],
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        _ = [event async for event in provider.stream(provider_request)]

    assert body.closed is True


async def test_ollama_stream_stops_at_completion(
    settings,
    provider_request,
):
    provider, body, _ = make_provider(
        settings,
        [
            make_event(
                'Resposta',
                done=True,
                done_reason='stop',
            ),
            make_event('Unexpected trailing content'),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert events == [
        ProviderDelta(content='Resposta'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        ),
    ]

    assert body.closed is True


class FailingByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks, error):
        self.chunks = chunks
        self.error = error
        self.closed = False

    @override
    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

        raise self.error

    @override
    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize(
    ('error_type', 'expected_code'),
    [
        (
            httpx.ConnectTimeout,
            ProviderErrorCode.GENERATION_TIMEOUT,
        ),
        (
            httpx.ReadTimeout,
            ProviderErrorCode.GENERATION_TIMEOUT,
        ),
        (
            httpx.WriteTimeout,
            ProviderErrorCode.GENERATION_TIMEOUT,
        ),
        (
            httpx.PoolTimeout,
            ProviderErrorCode.GENERATION_TIMEOUT,
        ),
        (
            httpx.ConnectError,
            ProviderErrorCode.PROVIDER_UNAVAILABLE,
        ),
        (
            httpx.RemoteProtocolError,
            ProviderErrorCode.PROVIDER_UNAVAILABLE,
        ),
    ],
)
async def test_ollama_stream_request_failure(
    settings,
    provider_request,
    error_type,
    expected_code,
):
    requests = []
    secret = 'fake-sensitive-transport-error'

    def handler(request):
        requests.append(request)
        raise error_type(secret, request=request)

    provider = OllamaProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        ProviderError,
        match=expected_code.value,
    ) as exc_info:
        _ = [event async for event in provider.stream(provider_request)]

    assert exc_info.value.code == expected_code
    assert secret not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
    assert len(requests) == 1


@pytest.mark.parametrize(
    ('error_type', 'expected_code'),
    [
        (
            httpx.ReadError,
            ProviderErrorCode.PROVIDER_UNAVAILABLE,
        ),
        (
            httpx.RemoteProtocolError,
            ProviderErrorCode.PROVIDER_UNAVAILABLE,
        ),
        (
            httpx.ReadTimeout,
            ProviderErrorCode.GENERATION_TIMEOUT,
        ),
        (
            httpx.DecodingError,
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE,
        ),
    ],
)
async def test_ollama_stream_failure_before_content(
    settings,
    provider_request,
    error_type,
    expected_code,
):
    body = FailingByteStream(
        [],
        error_type('Simulated failure.'),
    )

    def handler(request):
        return httpx.Response(
            200,
            headers={
                'content-type': 'application/x-ndjson',
            },
            stream=body,
        )

    provider = OllamaProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        ProviderError,
        match=expected_code.value,
    ) as exc_info:
        _ = [event async for event in provider.stream(provider_request)]

    assert exc_info.value.code == expected_code
    assert body.closed is True


@pytest.mark.parametrize(
    ('error_type', 'expected_code'),
    [
        (
            httpx.ReadError,
            ProviderErrorCode.STREAM_INTERRUPTED,
        ),
        (
            httpx.RemoteProtocolError,
            ProviderErrorCode.STREAM_INTERRUPTED,
        ),
        (
            httpx.ReadTimeout,
            ProviderErrorCode.GENERATION_TIMEOUT,
        ),
        (
            httpx.DecodingError,
            ProviderErrorCode.INVALID_PROVIDER_RESPONSE,
        ),
    ],
)
async def test_ollama_stream_failure_after_content(
    settings,
    provider_request,
    error_type,
    expected_code,
):
    secret = 'fake-sensitive-stream-error'

    body = FailingByteStream(
        [make_event('Resposta parcial')],
        error_type(secret),
    )

    def handler(request):
        return httpx.Response(
            200,
            headers={
                'content-type': 'application/x-ndjson',
            },
            stream=body,
        )

    provider = OllamaProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    stream = provider.stream(provider_request)

    try:
        assert await anext(stream) == ProviderDelta(
            content='Resposta parcial',
        )

        with pytest.raises(
            ProviderError,
            match=expected_code.value,
        ) as exc_info:
            await anext(stream)

        assert exc_info.value.code == expected_code
        assert secret not in str(exc_info.value)
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__ is True
        assert body.closed is True
    finally:
        await stream.aclose()


async def test_ollama_stream_full_http_contract(settings):
    settings = settings.model_copy(
        update={
            'OLLAMA_TEMPERATURE': 0.5,
            'OLLAMA_NUM_CTX': 8192,
            'OLLAMA_NUM_PREDICT': 1024,
            'OLLAMA_SEED': 123,
            'OLLAMA_KEEP_ALIVE': '10m',
            'CHAT_TIMEOUT_SECONDS': 60,
        },
    )

    provider_request = ProviderRequest(
        messages=(
            ProviderMessage(
                role=ProviderRole.SYSTEM,
                content='Assistente de suporte técnico.',
            ),
            ProviderMessage(
                role=ProviderRole.USER,
                content='Como configurar o PostgreSQL?',
            ),
            ProviderMessage(
                role=ProviderRole.ASSISTANT,
                content='Verifique a configuração inicial.',
            ),
            ProviderMessage(
                role=ProviderRole.USER,
                content='  Explique a próxima etapa.\nObrigado! 🚀  ',
            ),
        ),
    )

    provider, body, requests = make_provider(
        settings,
        [
            make_event('Primeira etapa. '),
            make_event(
                'Segunda etapa.',
                done=True,
                done_reason='stop',
                prompt_eval_count=150,
                eval_count=32,
            ),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert len(requests) == 1

    request = requests[0]

    assert request.method == 'POST'
    assert str(request.url) == 'http://ollama:11434/api/chat'
    assert request.headers['content-type'] == 'application/json'
    assert request.headers['accept'] == 'application/x-ndjson'
    assert request.headers['accept-encoding'] == 'identity'
    assert 'authorization' not in request.headers

    assert json.loads(request.content) == {
        'model': 'qwen2.5:7b',
        'messages': [
            {
                'role': 'system',
                'content': 'Assistente de suporte técnico.',
            },
            {
                'role': 'user',
                'content': 'Como configurar o PostgreSQL?',
            },
            {
                'role': 'assistant',
                'content': 'Verifique a configuração inicial.',
            },
            {
                'role': 'user',
                'content': ('  Explique a próxima etapa.\nObrigado! 🚀  '),
            },
        ],
        'stream': True,
        'keep_alive': '10m',
        'options': {
            'temperature': 0.5,
            'num_ctx': 8192,
            'num_predict': 1024,
            'seed': 123,
        },
    }

    assert request.extensions['timeout'] == {
        'connect': 5.0,
        'read': 60.0,
        'write': 60.0,
        'pool': 60.0,
    }

    assert events == [
        ProviderDelta(content='Primeira etapa. '),
        ProviderDelta(content='Segunda etapa.'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(
                input_tokens=150,
                output_tokens=32,
            ),
        ),
    ]

    assert body.closed is True


async def test_ollama_stream_http_request_excludes_credentials(
    settings,
    provider_request,
):
    secrets = {
        'DATABASE_URL': (
            'postgresql+asyncpg://fake-user:fake-db-secret'
            '@localhost/fake-database'
        ),
        'JWT_SECRET_KEY': 'fake-jwt-secret',
        'OPENAI_API_KEY': 'fake-openai-secret',
        'METRICS_TOKEN': 'fake-metrics-secret',
    }

    settings = settings.model_copy(update=secrets)

    provider, body, requests = make_provider(
        settings,
        [
            make_event(
                'Resposta segura.',
                done=True,
                done_reason='stop',
            ),
        ],
    )

    events = [event async for event in provider.stream(provider_request)]

    assert len(requests) == 1

    request = requests[0]

    serialized_request = '\n'.join([
        str(request.url),
        str(request.headers),
        request.content.decode('utf-8'),
    ])

    for secret in secrets.values():
        assert secret not in serialized_request

    assert 'fake-db-secret' not in serialized_request

    assert 'authorization' not in request.headers
    assert 'proxy-authorization' not in request.headers
    assert 'cookie' not in request.headers
    assert 'x-api-key' not in request.headers
    assert 'x-metrics-token' not in request.headers

    assert set(json.loads(request.content)) == {
        'model',
        'messages',
        'stream',
        'keep_alive',
        'options',
    }

    assert events == [
        ProviderDelta(content='Resposta segura.'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        ),
    ]

    assert body.closed is True


@pytest.mark.parametrize(
    'framing',
    [
        'single-chunk',
        'terminal-without-newline',
        'fragmented-crlf',
    ],
)
async def test_ollama_stream_chunk_boundaries(
    settings,
    provider_request,
    framing,
):
    first = make_event('Olá! ')
    second = make_event('Configuração concluída. 🚀')
    terminal = make_event(
        done=True,
        done_reason='stop',
        prompt_eval_count=42,
        eval_count=18,
    )

    if framing == 'single-chunk':
        chunks = [first + second + terminal]

    elif framing == 'terminal-without-newline':
        chunks = [
            first + second,
            terminal.removesuffix(b'\n'),
        ]

    else:
        content = (first + second + terminal).replace(b'\n', b'\r\n')

        chunks = [bytes([value]) for value in content]

    provider, body, requests = make_provider(
        settings,
        chunks,
    )

    events = [event async for event in provider.stream(provider_request)]

    assert events == [
        ProviderDelta(content='Olá! '),
        ProviderDelta(
            content='Configuração concluída. 🚀',
        ),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(
                input_tokens=42,
                output_tokens=18,
            ),
        ),
    ]

    assert len(requests) == 1
    assert body.closed is True


@pytest.mark.parametrize(
    'failure',
    [
        'model-mismatch',
        'invalid-json',
        'invalid-token-count',
        'unexpected-tool-calls',
    ],
)
async def test_ollama_stream_rejects_invalid_event_after_delta(
    settings,
    provider_request,
    failure,
):
    sensitive_marker = 'fake-sensitive-provider-content'

    invalid_event = {
        'model': 'qwen2.5:7b',
        'message': {
            'role': 'assistant',
            'content': sensitive_marker,
        },
        'done': True,
        'done_reason': 'stop',
        'prompt_eval_count': 20,
        'eval_count': 10,
    }

    if failure == 'model-mismatch':
        invalid_event['model'] = 'unauthorized-model'

    elif failure == 'invalid-token-count':
        invalid_event['eval_count'] = -1

    elif failure == 'unexpected-tool-calls':
        invalid_event['message']['tool_calls'] = [
            {
                'function': {
                    'name': 'unexpected_function',
                    'arguments': {},
                },
            },
        ]

    if failure == 'invalid-json':
        invalid_chunk = (f'{{invalid-json:{sensitive_marker}\n').encode(
            'utf-8'
        )
    else:
        invalid_chunk = (json.dumps(invalid_event) + '\n').encode('utf-8')

    provider, body, requests = make_provider(
        settings,
        [
            make_event('Conteudo parcial valido.'),
            invalid_chunk,
            make_event(
                'Evento posterior.',
                done=True,
                done_reason='stop',
            ),
        ],
    )

    received = []

    async def consume():
        async for event in provider.stream(provider_request):
            received.append(event)

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as error:
        await consume()

    assert received == [
        ProviderDelta(content='Conteudo parcial valido.'),
    ]

    assert str(error.value) == 'INVALID_PROVIDER_RESPONSE'
    assert sensitive_marker not in str(error.value)

    assert len(requests) == 1
    assert body.closed is True
