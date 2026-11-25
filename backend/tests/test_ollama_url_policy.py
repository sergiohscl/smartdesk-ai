import pytest
from pydantic import AnyHttpUrl

from app.core.ollama_url_policy import (
    validate_local_ollama_url,
)


@pytest.mark.parametrize(
    'url',
    [
        'http://ollama:11434',
        'http://localhost:11434',
        'http://127.0.0.1:11434',
        'http://[::1]:11434',
        'http://ollama:11434/',
        'https://localhost:11434',
    ],
)
def test_ollama_url_accepts_local_hosts(url):
    result = validate_local_ollama_url(url)

    assert isinstance(result, AnyHttpUrl)
    assert str(result) == str(AnyHttpUrl(url))


def test_ollama_url_accepts_validated_object():
    url = AnyHttpUrl('http://ollama:11434')

    assert validate_local_ollama_url(url) == url


@pytest.mark.parametrize(
    'url',
    [
        'https://api.openai.com',
        'https://ollama.com',
        'http://example.com:11434',
        'http://ollama.example.com:11434',
        'http://localhost.example.com:11434',
        'http://127.0.0.2:11434',
        'http://192.168.1.10:11434',
        'http://0.0.0.0:11434',
        'http://[::2]:11434',
    ],
)
def test_ollama_url_rejects_unauthorized_hosts(url):
    with pytest.raises(
        ValueError,
        match='Ollama must use a local host',
    ):
        validate_local_ollama_url(url)


@pytest.mark.parametrize(
    'url',
    [
        'http://user@localhost:11434',
        'http://user:password@localhost:11434',
        'http://localhost:11434/api/chat',
        'http://localhost:11434/custom',
        'http://localhost:11434?token=secret',
        'http://localhost:11434#fragment',
        'http://localhost:11434?',
        'http://localhost:11434#',
    ],
)
def test_ollama_url_rejects_unexpected_components(url):
    with pytest.raises(
        ValueError,
        match='Invalid Ollama base URL',
    ):
        validate_local_ollama_url(url)


@pytest.mark.parametrize(
    'url',
    [
        None,
        True,
        123,
        [],
        {},
        '',
        'invalid-url',
        'ftp://localhost:11434',
        'file:///tmp/ollama',
        'http://',
    ],
)
def test_ollama_url_rejects_invalid_values(url):
    with pytest.raises(
        ValueError,
        match='Invalid Ollama base URL',
    ):
        validate_local_ollama_url(url)


def test_ollama_url_error_is_sanitized():
    secret = 'fake-sensitive-password'
    url = f'http://user:{secret}@localhost:11434'

    with pytest.raises(
        ValueError,
        match='Invalid Ollama base URL',
    ) as exc_info:
        validate_local_ollama_url(url)

    assert secret not in str(exc_info.value)


def test_ollama_url_parse_error_is_sanitized():
    secret = 'fake-sensitive-invalid-url'

    with pytest.raises(
        ValueError,
        match='Invalid Ollama base URL',
    ) as exc_info:
        validate_local_ollama_url(secret)

    assert secret not in str(exc_info.value)
    assert exc_info.value.__suppress_context__ is True
