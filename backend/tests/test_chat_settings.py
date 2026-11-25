import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from app.core.settings import Settings


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
    )


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)


def make_settings(**overrides):
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://test:test@localhost/test',
        JWT_SECRET_KEY='test-secret',
        **overrides,
    )


def test_chat_settings_defaults():
    settings = make_settings()

    assert settings.CHAT_ENABLED is True
    assert settings.CHAT_PROVIDER == 'ollama'
    assert settings.CHAT_MODEL == 'qwen2.5:7b'
    assert str(settings.OLLAMA_BASE_URL) == 'http://ollama:11434/'
    assert settings.OLLAMA_TEMPERATURE == 0.1
    assert settings.OLLAMA_NUM_CTX == 4096
    assert settings.OLLAMA_NUM_PREDICT == 768
    assert settings.OLLAMA_SEED == 42
    assert settings.OLLAMA_KEEP_ALIVE == '5m'
    assert settings.CHAT_TIMEOUT_SECONDS == 120
    assert settings.CHAT_MAX_MESSAGE_CHARS == 8000
    assert settings.CHAT_MAX_TITLE_CHARS == 150
    assert settings.CHAT_MAX_CONTEXT_MESSAGES == 20
    assert settings.CHAT_DAILY_USER_LIMIT == 50
    assert settings.CHAT_REQUESTS_PER_MINUTE == 5
    assert settings.CHAT_MAX_CONCURRENT_PER_USER == 1
    assert settings.CHAT_MAX_CONCURRENT_GLOBAL == 1
    assert settings.CHAT_PROMPT_VERSION == 'v2'
    assert settings.CHAT_ALLOW_PAID_FALLBACK is False


def test_chat_settings_preserve_existing_defaults():
    settings = make_settings()

    assert settings.JWT_ALGORITHM == 'HS256'
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.OPENAI_API_KEY is None
    assert settings.OPENAI_MODEL == 'gpt-6-luna'
    assert settings.AI_TIMEOUT_SECONDS == 15
    assert settings.AI_MAX_OUTPUT_TOKENS == 300
    assert settings.AI_MAX_DESCRIPTION_CHARS == 4000
    assert settings.AI_DAILY_USER_LIMIT == 20
    assert settings.METRICS_TOKEN is None


def test_chat_settings_can_be_disabled():
    settings = make_settings(CHAT_ENABLED=False)

    assert settings.CHAT_ENABLED is False


def test_chat_settings_normalize_model():
    settings = make_settings(CHAT_MODEL='  qwen2.5:7b  ')

    assert settings.CHAT_MODEL == 'qwen2.5:7b'


@pytest.mark.parametrize(
    'url',
    [
        'http://ollama:11434',
        'http://localhost:11434',
        'http://127.0.0.1:11434',
        'http://[::1]:11434',
        'https://ollama:11434',
    ],
)
def test_chat_settings_valid_ollama_url(url):
    settings = make_settings(OLLAMA_BASE_URL=url)

    assert str(settings.OLLAMA_BASE_URL) == f'{url}/'


@pytest.mark.parametrize(
    'url',
    [
        'not-a-url',
        'ftp://ollama:11434',
        'http://user:password@ollama:11434',
        'http://ollama:11434/api/chat',
        'http://ollama:11434?token=secret',
        'http://ollama:11434#fragment',
        'https://api.openai.com',
        'https://ollama.com',
        'http://192.168.1.10:11434',
        'http://ollama.example.com:11434',
    ],
)
def test_chat_settings_invalid_ollama_url(url):
    with pytest.raises(ValidationError):
        make_settings(OLLAMA_BASE_URL=url)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('CHAT_ENABLED', 'invalid'),
        ('CHAT_PROVIDER', 'openai'),
        ('CHAT_PROVIDER', 'unknown'),
        ('CHAT_PROVIDER', ''),
        ('CHAT_MODEL', ''),
        ('CHAT_MODEL', '   '),
        ('CHAT_MODEL', 'a' * 101),
        ('CHAT_MODEL', 'model\x00name'),
        ('OLLAMA_TEMPERATURE', -0.1),
        ('OLLAMA_TEMPERATURE', 2.1),
        ('OLLAMA_TEMPERATURE', float('nan')),
        ('OLLAMA_TEMPERATURE', float('inf')),
        ('OLLAMA_NUM_CTX', 511),
        ('OLLAMA_NUM_CTX', 32769),
        ('OLLAMA_NUM_PREDICT', 0),
        ('OLLAMA_NUM_PREDICT', 8193),
        ('OLLAMA_SEED', -1),
        ('OLLAMA_SEED', 2147483648),
        ('OLLAMA_KEEP_ALIVE', ''),
        ('OLLAMA_KEEP_ALIVE', '-1'),
        ('OLLAMA_KEEP_ALIVE', 'forever'),
        ('OLLAMA_KEEP_ALIVE', '5d'),
        ('CHAT_TIMEOUT_SECONDS', 0),
        ('CHAT_TIMEOUT_SECONDS', 601),
        ('CHAT_MAX_MESSAGE_CHARS', 0),
        ('CHAT_MAX_MESSAGE_CHARS', 8001),
        ('CHAT_MAX_TITLE_CHARS', 0),
        ('CHAT_MAX_TITLE_CHARS', 151),
        ('CHAT_MAX_CONTEXT_MESSAGES', 0),
        ('CHAT_MAX_CONTEXT_MESSAGES', 101),
        ('CHAT_DAILY_USER_LIMIT', 0),
        ('CHAT_DAILY_USER_LIMIT', 10001),
        ('CHAT_REQUESTS_PER_MINUTE', 0),
        ('CHAT_REQUESTS_PER_MINUTE', 1001),
        ('CHAT_MAX_CONCURRENT_PER_USER', 0),
        ('CHAT_MAX_CONCURRENT_PER_USER', 101),
        ('CHAT_MAX_CONCURRENT_GLOBAL', 0),
        ('CHAT_MAX_CONCURRENT_GLOBAL', 101),
        ('CHAT_PROMPT_VERSION', 'v1'),
        ('CHAT_PROMPT_VERSION', ''),
        ('CHAT_ALLOW_PAID_FALLBACK', True),
        ('CHAT_ALLOW_PAID_FALLBACK', 'true'),
    ],
)
def test_chat_settings_invalid_values(field, value):
    with pytest.raises(ValidationError):
        make_settings(**{field: value})


@pytest.mark.parametrize(
    ('context_size', 'output_limit'),
    [
        (512, 512),
        (512, 768),
        (4096, 4096),
        (4096, 8192),
    ],
)
def test_chat_settings_invalid_context_budget(
    context_size,
    output_limit,
):
    with pytest.raises(
        ValidationError,
        match='Output limit must be smaller',
    ):
        make_settings(
            OLLAMA_NUM_CTX=context_size,
            OLLAMA_NUM_PREDICT=output_limit,
        )


@pytest.mark.parametrize(
    ('user_limit', 'global_limit'),
    [
        (2, 1),
        (5, 4),
        (100, 99),
    ],
)
def test_chat_settings_invalid_concurrency(
    user_limit,
    global_limit,
):
    with pytest.raises(
        ValidationError,
        match='User concurrency cannot exceed',
    ):
        make_settings(
            CHAT_MAX_CONCURRENT_PER_USER=user_limit,
            CHAT_MAX_CONCURRENT_GLOBAL=global_limit,
        )


@pytest.mark.parametrize(
    ('context_size', 'output_limit', 'expected'),
    [
        (4096, 768, 3328),
        (2048, 512, 1536),
        (8192, 1024, 7168),
        (512, 1, 511),
    ],
)
def test_chat_settings_input_token_budget(
    context_size,
    output_limit,
    expected,
):
    settings = make_settings(
        OLLAMA_NUM_CTX=context_size,
        OLLAMA_NUM_PREDICT=output_limit,
    )

    assert settings.chat_input_token_budget == expected


@pytest.mark.parametrize(
    'keep_alive',
    ['0', '0s', '30s', '5m', '1h'],
)
def test_chat_settings_valid_keep_alive(keep_alive):
    settings = make_settings(OLLAMA_KEEP_ALIVE=keep_alive)

    assert settings.OLLAMA_KEEP_ALIVE == keep_alive


@pytest.mark.parametrize(
    ('user_limit', 'global_limit'),
    [
        (1, 1),
        (1, 2),
        (2, 2),
        (2, 5),
    ],
)
def test_chat_settings_valid_concurrency(
    user_limit,
    global_limit,
):
    settings = make_settings(
        CHAT_MAX_CONCURRENT_PER_USER=user_limit,
        CHAT_MAX_CONCURRENT_GLOBAL=global_limit,
    )

    assert settings.CHAT_MAX_CONCURRENT_PER_USER == user_limit
    assert settings.CHAT_MAX_CONCURRENT_GLOBAL == global_limit


def test_chat_settings_environment_variables(monkeypatch):
    monkeypatch.setenv('CHAT_ENABLED', 'false')
    monkeypatch.setenv('CHAT_MODEL', '  qwen2.5:7b  ')
    monkeypatch.setenv(
        'OLLAMA_BASE_URL',
        'http://localhost:11434',
    )
    monkeypatch.setenv('OLLAMA_TEMPERATURE', '0.2')
    monkeypatch.setenv('OLLAMA_NUM_CTX', '2048')
    monkeypatch.setenv('OLLAMA_NUM_PREDICT', '512')
    monkeypatch.setenv('CHAT_DAILY_USER_LIMIT', '25')
    monkeypatch.setenv('CHAT_TIMEOUT_SECONDS', '180')
    monkeypatch.setenv('CHAT_ALLOW_PAID_FALLBACK', 'false')

    settings = make_settings()

    assert settings.CHAT_ENABLED is False
    assert settings.CHAT_MODEL == 'qwen2.5:7b'
    assert str(settings.OLLAMA_BASE_URL) == 'http://localhost:11434/'
    assert settings.OLLAMA_TEMPERATURE == 0.2
    assert settings.OLLAMA_NUM_CTX == 2048
    assert settings.OLLAMA_NUM_PREDICT == 512
    assert settings.CHAT_DAILY_USER_LIMIT == 25
    assert settings.CHAT_TIMEOUT_SECONDS == 180
    assert settings.CHAT_ALLOW_PAID_FALLBACK is False
    assert settings.chat_input_token_budget == 1536


def test_chat_settings_reject_paid_fallback_from_environment(
    monkeypatch,
):
    monkeypatch.setenv('CHAT_ALLOW_PAID_FALLBACK', 'true')

    with pytest.raises(
        ValidationError,
        match='Paid fallback is not allowed',
    ):
        make_settings()


def test_chat_settings_constructor_overrides_environment(
    monkeypatch,
):
    monkeypatch.setenv('CHAT_DAILY_USER_LIMIT', '25')

    settings = make_settings(CHAT_DAILY_USER_LIMIT=10)

    assert settings.CHAT_DAILY_USER_LIMIT == 10


@pytest.mark.parametrize(
    'model',
    [
        'qwen2.5:3b',
        'qwen2.5:latest',
        'qwen2.5:7b-cloud',
        'deepseek-r1:7b',
        'gpt-4o',
        'unknown',
        'QWEN2.5:7B',
        'qwen2.5',
    ],
)
def test_chat_settings_rejects_unauthorized_model(model):
    with pytest.raises(
        ValidationError,
        match='Chat model is not authorized',
    ):
        make_settings(CHAT_MODEL=model)


def test_chat_settings_rejects_unauthorized_environment_model(
    monkeypatch,
):
    monkeypatch.setenv('CHAT_MODEL', 'qwen2.5:3b')

    with pytest.raises(
        ValidationError,
        match='Chat model is not authorized',
    ):
        make_settings()
