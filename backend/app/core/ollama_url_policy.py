from pydantic import AnyHttpUrl, ValidationError

ALLOWED_OLLAMA_HOSTS = frozenset({
    'ollama',
    'localhost',
    '127.0.0.1',
    '[::1]',
})


def validate_local_ollama_url(value: object) -> AnyHttpUrl:
    """Validate the Ollama URL before creating an HTTP client."""

    if not isinstance(value, (str, AnyHttpUrl)):
        raise ValueError('Invalid Ollama base URL.')

    try:
        url = AnyHttpUrl(str(value))
    except ValidationError:
        raise ValueError('Invalid Ollama base URL.') from None

    if (
        url.username is not None
        or url.password is not None
        or url.query is not None
        or url.fragment is not None
        or url.path not in {None, '', '/'}
    ):
        raise ValueError('Invalid Ollama base URL.')

    if url.host not in ALLOWED_OLLAMA_HOSTS:
        raise ValueError('Ollama must use a local host.')

    return url
