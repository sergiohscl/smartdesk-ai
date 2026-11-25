import pytest

from app.services.providers import (
    ProviderCompletion,
    ProviderDelta,
    ProviderError,
    ProviderErrorCode,
    ProviderFinishReason,
    ProviderUsage,
)
from app.services.providers.ollama_events import (
    parse_ollama_event,
)


def parse_event(data):
    return parse_ollama_event(
        data,
        expected_model='qwen2.5:7b',
    )


def make_event(
    content='',
    *,
    done=False,
    **fields,
):
    return {
        'model': 'qwen2.5:7b',
        'message': {
            'role': 'assistant',
            'content': content,
        },
        'done': done,
        **fields,
    }


@pytest.mark.parametrize(
    'content',
    [
        'Hello',
        'Olá, usuário!',
        ' ',
        '\n',
        '  Preserve whitespace  ',
        'SELECT * FROM tickets;',
        'Resposta técnica 🚀',
    ],
)
def test_ollama_event_delta(content):
    events = parse_event(make_event(content))

    assert events == (ProviderDelta(content=content),)


def test_ollama_event_empty_delta():
    assert parse_event(make_event()) == ()


@pytest.mark.parametrize(
    ('reason', 'expected'),
    [
        ('stop', ProviderFinishReason.STOP),
        ('length', ProviderFinishReason.LENGTH),
    ],
)
def test_ollama_event_completion(reason, expected):
    data = make_event(
        done=True,
        done_reason=reason,
        prompt_eval_count=100,
        eval_count=50,
    )

    assert parse_event(data) == (
        ProviderCompletion(
            finish_reason=expected,
            usage=ProviderUsage(
                input_tokens=100,
                output_tokens=50,
            ),
        ),
    )


def test_ollama_event_final_content():
    data = make_event(
        'Último fragmento',
        done=True,
        done_reason='stop',
    )

    assert parse_event(data) == (
        ProviderDelta(content='Último fragmento'),
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        ),
    )


@pytest.mark.parametrize(
    ('fields', 'expected'),
    [
        ({}, ProviderUsage()),
        (
            {'prompt_eval_count': 100},
            ProviderUsage(input_tokens=100),
        ),
        (
            {'eval_count': 50},
            ProviderUsage(output_tokens=50),
        ),
        (
            {'prompt_eval_count': 0, 'eval_count': 0},
            ProviderUsage(input_tokens=0, output_tokens=0),
        ),
    ],
)
def test_ollama_event_usage(fields, expected):
    data = make_event(
        done=True,
        done_reason='stop',
        **fields,
    )

    assert parse_event(data) == (
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=expected,
        ),
    )


def test_ollama_event_ignores_extra_metadata():
    data = make_event(
        'Hello',
        model='qwen2.5:7b',
        created_at='2026-11-25T12:00:00Z',
        total_duration=123456,
    )

    assert parse_event(data) == (ProviderDelta(content='Hello'),)


@pytest.mark.parametrize(
    'done',
    [None, 0, 1, 'true', 'false', [], {}],
)
def test_ollama_event_invalid_done(done):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(make_event(done=done))


@pytest.mark.parametrize(
    'message',
    [
        None,
        [],
        'invalid',
        {},
        {'role': 'user', 'content': 'Hello'},
        {'role': 'system', 'content': 'Hello'},
        {'role': 'assistant'},
        {'role': 'assistant', 'content': None},
        {'role': 'assistant', 'content': 123},
        {'role': 'assistant', 'content': chr(0)},
    ],
)
def test_ollama_event_invalid_message(message):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(make_event(message=message))


@pytest.mark.parametrize(
    'reason',
    [None, '', 'unknown', 'cancelled', 123, [], {}],
)
def test_ollama_event_invalid_finish_reason(reason):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(make_event(done=True, done_reason=reason))


@pytest.mark.parametrize(
    'field',
    ['prompt_eval_count', 'eval_count'],
)
@pytest.mark.parametrize(
    'value',
    [-1, True, False, 1.5, '10', None, [], {}],
)
def test_ollama_event_invalid_token_count(field, value):
    data = make_event(
        done=True,
        done_reason='stop',
        **{field: value},
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


def test_ollama_event_missing_done():
    data = make_event('Hello')
    del data['done']

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


def test_ollama_event_missing_message():
    data = make_event('Hello')
    del data['message']

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


def test_ollama_event_missing_finish_reason():
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(make_event(done=True))


def test_ollama_event_sanitizes_provider_error():
    secret = 'fake-sensitive-provider-error'

    with pytest.raises(
        ProviderError,
        match='PROVIDER_REQUEST_ERROR',
    ) as exc_info:
        parse_event({'error': secret})

    assert exc_info.value.code is (ProviderErrorCode.PROVIDER_REQUEST_ERROR)
    assert secret not in str(exc_info.value)


def test_ollama_event_invalid_completion_is_atomic():
    data = make_event(
        'Partial content',
        done=True,
        done_reason='invalid',
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


@pytest.mark.parametrize(
    'field',
    ['prompt_eval_count', 'eval_count'],
)
@pytest.mark.parametrize(
    'value',
    [0, 1, 2147483646, 2147483647],
)
def test_ollama_event_token_boundary_accepts(field, value):
    data = make_event(
        done=True,
        done_reason='stop',
        **{field: value},
    )

    completion = parse_event(data)[0]

    assert isinstance(completion, ProviderCompletion)

    if field == 'prompt_eval_count':
        assert completion.usage.input_tokens == value
    else:
        assert completion.usage.output_tokens == value


@pytest.mark.parametrize(
    'field',
    ['prompt_eval_count', 'eval_count'],
)
@pytest.mark.parametrize(
    'value',
    [2147483648, 4294967295, 10**100],
)
def test_ollama_event_token_boundary_rejects(field, value):
    data = make_event(
        done=True,
        done_reason='stop',
        **{field: value},
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


@pytest.mark.parametrize(
    'content',
    [
        chr(0xD800),
        chr(0xDFFF),
        'Invalid ' + chr(0xD800),
        chr(0xD800) + chr(0xDC00),
    ],
)
def test_ollama_event_unicode_rejects_surrogates(content):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        parse_event(make_event(content))

    assert exc_info.value.__suppress_context__ is True


@pytest.mark.parametrize(
    'content',
    [
        'Olá, usuário!',
        'Resposta técnica 🚀',
        '日本語',
        'Texto com acentuação: ação',
    ],
)
def test_ollama_event_unicode_accepts_valid_content(content):
    assert parse_event(make_event(content)) == (
        ProviderDelta(content=content),
    )


@pytest.mark.parametrize(
    'fields',
    [
        {'done_reason': 'stop'},
        {'done_reason': 'length'},
        {'done_reason': None},
        {'prompt_eval_count': 100},
        {'eval_count': 50},
        {'prompt_eval_count': 0, 'eval_count': 0},
    ],
)
def test_ollama_event_intermediate_rejects_terminal_fields(fields):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(make_event('Hello', **fields))


@pytest.mark.parametrize(
    'error',
    [None, True, False, 123, [], {}, '', '   '],
)
def test_ollama_event_error_rejects_invalid_structure(error):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event({'error': error})


@pytest.mark.parametrize(
    'error',
    [
        'model not found',
        'internal provider failure',
        'fake-sensitive-content',
    ],
)
def test_ollama_event_error_preserves_sanitization(error):
    with pytest.raises(
        ProviderError,
        match='PROVIDER_REQUEST_ERROR',
    ) as exc_info:
        parse_event({'error': error})

    assert error not in str(exc_info.value)


@pytest.mark.parametrize(
    'tool_calls',
    [
        None,
        True,
        {},
        'execute',
        [{'function': {'name': 'execute_command'}}],
        [{'function': {'name': 'delete_ticket'}}],
    ],
)
def test_ollama_event_tools_rejects_unexpected_calls(tool_calls):
    data = make_event('Hello')
    data['message']['tool_calls'] = tool_calls

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


def test_ollama_event_tools_accepts_empty_list():
    data = make_event('Hello')
    data['message']['tool_calls'] = []

    assert parse_event(data) == (ProviderDelta(content='Hello'),)


def test_ollama_identity_accepts_model():
    data = make_event('Hello')

    assert parse_ollama_event(
        data,
        expected_model='qwen2.5:7b',
    ) == (ProviderDelta(content='Hello'),)


@pytest.mark.parametrize(
    'model',
    [
        'qwen2.5:3b',
        'qwen2.5:latest',
        'qwen2.5:7b-cloud',
        'gpt-4o',
        'unknown',
        'QWEN2.5:7B',
        ' qwen2.5:7b ',
        '',
        None,
        True,
        False,
        123,
        [],
        {},
    ],
)
def test_ollama_identity_rejects_invalid_model(model):
    data = make_event('Hello', model=model)

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


def test_ollama_identity_rejects_missing_model():
    data = make_event('Hello')
    del data['model']

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


@pytest.mark.parametrize(
    'reason',
    ['stop', 'length'],
)
def test_ollama_identity_accepts_completion(reason):
    data = make_event(
        done=True,
        done_reason=reason,
    )

    assert parse_event(data) == (
        ProviderCompletion(
            finish_reason=ProviderFinishReason(reason),
            usage=ProviderUsage(),
        ),
    )


@pytest.mark.parametrize(
    'reason',
    ['stop', 'length'],
)
def test_ollama_identity_rejects_invalid_completion(reason):
    data = make_event(
        'Unexpected content',
        done=True,
        done_reason=reason,
        model='unknown',
    )

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(data)


def test_ollama_identity_error_is_sanitized():
    secret = 'fake-sensitive-model-name'
    data = make_event('Hello', model=secret)

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        parse_event(data)

    assert secret not in str(exc_info.value)


def test_ollama_identity_provider_error_without_model():
    with pytest.raises(
        ProviderError,
        match='PROVIDER_REQUEST_ERROR',
    ):
        parse_event({'error': 'Provider failure'})


def test_ollama_identity_uses_expected_model():
    data = make_event('Hello')

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ollama_event(
            data,
            expected_model='different-model',
        )


def test_ollama_identity_rejects_model_change():
    first = make_event('First fragment')
    second = make_event(
        'Second fragment',
        model='qwen2.5:3b',
    )

    assert parse_event(first) == (ProviderDelta(content='First fragment'),)

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_event(second)
