from inspect import isabstract

import httpx
import pytest
from pydantic_settings import SettingsConfigDict

from app.core.settings import Settings
from app.services.providers import (
    AIProvider,
    OllamaProvider,
    ProviderMessage,
    ProviderRequest,
    ProviderRole,
)


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_OLLAMA_TEST_',
    )


@pytest.fixture
def settings():
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://test:test@localhost/test',
        JWT_SECRET_KEY='test-secret-not-for-production',
    )


def test_ollama_provider_implements_contract(settings):
    provider = OllamaProvider(settings)

    assert isinstance(provider, AIProvider)
    assert not isabstract(OllamaProvider)


def test_ollama_provider_default_model(settings):
    provider = OllamaProvider(settings)

    assert provider.model == 'qwen2.5:7b'


def test_ollama_provider_rejects_unauthorized_model(settings):
    settings = settings.model_copy(update={'CHAT_MODEL': 'qwen2.5:3b'})

    provider = OllamaProvider(settings)

    with pytest.raises(
        ValueError,
        match='Chat model is not authorized',
    ):
        _ = provider.model


async def test_ollama_provider_client_base_url(settings):
    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert str(client.base_url) == 'http://ollama:11434/'


async def test_ollama_provider_disables_redirects(settings):
    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert client.follow_redirects is False


async def test_ollama_provider_disables_environment_proxy(settings):
    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert client.trust_env is False


async def test_ollama_provider_client_timeouts(settings):
    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert client.timeout.connect == 5.0
        assert client.timeout.read == 120.0
        assert client.timeout.write == 120.0
        assert client.timeout.pool == 120.0


async def test_ollama_provider_custom_timeout(settings):
    settings = settings.model_copy(update={'CHAT_TIMEOUT_SECONDS': 60})

    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert client.timeout.read == 60.0


async def test_ollama_provider_client_is_closed(settings):
    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert client.is_closed is False

    assert client.is_closed is True


async def test_ollama_provider_accepts_mock_transport(settings):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)

        return httpx.Response(
            200,
            json={'status': 'ok'},
        )

    transport = httpx.MockTransport(handler)

    provider = OllamaProvider(
        settings,
        transport=transport,
    )

    async with provider._create_client() as client:
        response = await client.get('/api/version')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    assert len(requests) == 1
    assert requests[0].method == 'GET'
    assert str(requests[0].url) == ('http://ollama:11434/api/version')


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


def test_ollama_payload_default(settings, provider_request):
    provider = OllamaProvider(settings)

    payload = provider._build_payload(provider_request)

    assert payload == {
        'model': 'qwen2.5:7b',
        'messages': [
            {
                'role': 'user',
                'content': 'Como configurar o PostgreSQL?',
            },
        ],
        'stream': True,
        'keep_alive': '5m',
        'options': {
            'temperature': 0.1,
            'num_ctx': 4096,
            'num_predict': 768,
            'seed': 42,
        },
    }


def test_ollama_payload_rejects_unauthorized_model(
    settings,
    provider_request,
):
    settings = settings.model_copy(update={'CHAT_MODEL': 'qwen2.5:3b'})

    provider = OllamaProvider(settings)

    with pytest.raises(
        ValueError,
        match='Chat model is not authorized',
    ):
        provider._build_payload(provider_request)


def test_ollama_payload_stream_enabled(settings, provider_request):
    provider = OllamaProvider(settings)

    payload = provider._build_payload(provider_request)

    assert payload['stream'] is True


def test_ollama_payload_custom_options(settings, provider_request):
    settings = settings.model_copy(
        update={
            'OLLAMA_TEMPERATURE': 0.5,
            'OLLAMA_NUM_CTX': 8192,
            'OLLAMA_NUM_PREDICT': 1024,
            'OLLAMA_SEED': 123,
            'OLLAMA_KEEP_ALIVE': '10m',
        }
    )

    provider = OllamaProvider(settings)

    payload = provider._build_payload(provider_request)

    assert payload['options'] == {
        'temperature': 0.5,
        'num_ctx': 8192,
        'num_predict': 1024,
        'seed': 123,
    }

    assert payload['keep_alive'] == '10m'


def test_ollama_payload_preserves_message_order(settings):
    provider = OllamaProvider(settings)

    request = ProviderRequest(
        messages=(
            ProviderMessage(
                role=ProviderRole.SYSTEM,
                content='You are a technical assistant.',
            ),
            ProviderMessage(
                role=ProviderRole.USER,
                content='First question.',
            ),
            ProviderMessage(
                role=ProviderRole.ASSISTANT,
                content='First answer.',
            ),
            ProviderMessage(
                role=ProviderRole.USER,
                content='Second question.',
            ),
        ),
    )

    payload = provider._build_payload(request)

    assert payload['messages'] == [
        {
            'role': 'system',
            'content': 'You are a technical assistant.',
        },
        {
            'role': 'user',
            'content': 'First question.',
        },
        {
            'role': 'assistant',
            'content': 'First answer.',
        },
        {
            'role': 'user',
            'content': 'Second question.',
        },
    ]


@pytest.mark.parametrize(
    'content',
    [
        'Configuração do PostgreSQL',
        'Primeira linha\nSegunda linha',
        '  Preserve whitespace  ',
        'SELECT * FROM tickets;',
        'Olá, usuário! 🚀',
        '```python\nprint("Hello")\n```',
    ],
)
def test_ollama_payload_preserves_content(settings, content):
    provider = OllamaProvider(settings)

    request = ProviderRequest(
        messages=(
            ProviderMessage(
                role=ProviderRole.USER,
                content=content,
            ),
        ),
    )

    payload = provider._build_payload(request)

    assert payload['messages'] == [
        {
            'role': 'user',
            'content': content,
        },
    ]


def test_ollama_payload_has_only_expected_fields(
    settings,
    provider_request,
):
    provider = OllamaProvider(settings)

    payload = provider._build_payload(provider_request)

    assert set(payload) == {
        'model',
        'messages',
        'stream',
        'keep_alive',
        'options',
    }


def test_ollama_payload_does_not_expose_credentials(
    settings,
    provider_request,
):
    settings = settings.model_copy(
        update={
            'OPENAI_API_KEY': 'fake-openai-secret',
            'METRICS_TOKEN': 'fake-metrics-secret',
        }
    )

    provider = OllamaProvider(settings)

    payload = provider._build_payload(provider_request)

    serialized = str(payload)

    assert settings.DATABASE_URL not in serialized
    assert settings.JWT_SECRET_KEY not in serialized
    assert settings.OPENAI_API_KEY not in serialized
    assert settings.METRICS_TOKEN not in serialized


def test_ollama_payload_returns_independent_objects(
    settings,
    provider_request,
):
    provider = OllamaProvider(settings)

    first = provider._build_payload(provider_request)
    second = provider._build_payload(provider_request)

    assert first == second
    assert first is not second
    assert first['messages'] is not second['messages']
    assert first['options'] is not second['options']


def test_ollama_payload_is_json_serializable(
    settings,
    provider_request,
):
    provider = OllamaProvider(settings)

    payload = provider._build_payload(provider_request)

    request = httpx.Request(
        'POST',
        'http://ollama:11434/api/chat',
        json=payload,
    )

    assert request.headers['content-type'] == 'application/json'
    assert request.content


@pytest.mark.parametrize(
    'model',
    [
        'qwen2.5:latest',
        'qwen2.5:7b-cloud',
        'gpt-4o',
        'unknown',
        None,
        [],
    ],
)
def test_ollama_provider_rejects_model_copy_bypass(
    settings,
    provider_request,
    model,
):
    settings = settings.model_copy(
        update={'CHAT_MODEL': model},
    )

    provider = OllamaProvider(settings)

    with pytest.raises(
        ValueError,
        match='Chat model is not authorized',
    ):
        _ = provider.model

    with pytest.raises(
        ValueError,
        match='Chat model is not authorized',
    ):
        provider._build_payload(provider_request)


@pytest.mark.parametrize(
    'url',
    [
        'https://api.openai.com',
        'https://ollama.com',
        'http://localhost.example.com:11434',
        'http://user:password@localhost:11434',
        'http://localhost:11434/api/chat',
        'http://localhost:11434?token=secret',
        'http://localhost:11434#fragment',
        'ftp://localhost:11434',
        None,
        [],
    ],
)
async def test_ollama_provider_rejects_url_copy_bypass(
    settings,
    provider_request,
    url,
):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(500)

    settings = settings.model_copy(
        update={'OLLAMA_BASE_URL': url},
    )

    provider = OllamaProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ValueError, match='Ollama'):
        async with provider._create_client():
            pytest.fail('Invalid URL accepted.')

    with pytest.raises(ValueError, match='Ollama'):
        _ = [event async for event in provider.stream(provider_request)]

    assert requests == []


async def test_ollama_provider_rejects_url_mutation(
    settings,
    provider_request,
):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(500)

    provider = OllamaProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    settings.OLLAMA_BASE_URL = 'https://api.openai.com'

    with pytest.raises(
        ValueError,
        match='Ollama must use a local host',
    ):
        _ = [event async for event in provider.stream(provider_request)]

    assert requests == []


async def test_ollama_provider_accepts_valid_url_copy(
    settings,
):
    settings = settings.model_copy(
        update={
            'OLLAMA_BASE_URL': 'http://127.0.0.1:11434',
        },
    )

    provider = OllamaProvider(settings)

    async with provider._create_client() as client:
        assert str(client.base_url) == 'http://127.0.0.1:11434/'
