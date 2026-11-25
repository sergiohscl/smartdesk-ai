import json

import pytest

from app.services.providers import (
    ProviderError,
    ProviderErrorCode,
)
from app.services.providers.ndjson import parse_ndjson_line


@pytest.mark.parametrize(
    'line',
    ['', ' ', '\t', '\r\n', '  \t  '],
)
def test_ndjson_ignores_empty_lines(line):
    assert parse_ndjson_line(line) is None


@pytest.mark.parametrize(
    'data',
    [
        {},
        {'done': False},
        {'done': True, 'done_reason': 'stop'},
        {'message': {'role': 'assistant', 'content': 'Hello'}},
        {'prompt_eval_count': 100, 'eval_count': 20},
    ],
)
def test_ndjson_parses_valid_objects(data):
    assert parse_ndjson_line(json.dumps(data)) == data


@pytest.mark.parametrize(
    'content',
    [
        'Olá, usuário!',
        '  Preserve whitespace  ',
        'Primeira linha\nSegunda linha',
        'SELECT * FROM tickets;',
        '```python\nprint("Hello")\n```',
        'Resposta técnica 🚀',
    ],
)
def test_ndjson_preserves_message_content(content):
    data = {
        'message': {
            'role': 'assistant',
            'content': content,
        },
        'done': False,
    }

    result = parse_ndjson_line(json.dumps(data, ensure_ascii=False))

    assert result == data


@pytest.mark.parametrize(
    'line',
    [
        '{',
        '{"done":',
        '{"done": false',
        '{"done": false,}',
        "{'done': False}",
        '{"done": False}',
        'invalid json',
        '{} {}',
        '{"done": false}\n{"done": true}',
    ],
)
def test_ndjson_rejects_malformed_json(line):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        parse_ndjson_line(line)

    assert exc_info.value.code is (ProviderErrorCode.INVALID_PROVIDER_RESPONSE)


@pytest.mark.parametrize(
    'line',
    [
        'null',
        'true',
        'false',
        '123',
        '1.5',
        '"text"',
        '[]',
        '[{"done": true}]',
    ],
)
def test_ndjson_rejects_non_object_values(line):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


@pytest.mark.parametrize(
    'line',
    [
        '{"value": NaN}',
        '{"value": Infinity}',
        '{"value": -Infinity}',
        '{"nested": {"value": NaN}}',
        '{"values": [Infinity]}',
    ],
)
def test_ndjson_rejects_nonstandard_constants(line):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


def test_ndjson_accepts_surrounding_whitespace():
    result = parse_ndjson_line('  {"done": false}  \r\n')

    assert result == {'done': False}


def test_ndjson_error_does_not_expose_raw_response():
    secret = 'fake-sensitive-provider-content'

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        parse_ndjson_line('{"secret": "' + secret)

    assert secret not in str(exc_info.value)
    assert exc_info.value.__suppress_context__ is True


def test_ndjson_rejects_excessive_nesting():
    line = '{"nested":' + '[' * 2000 + '0' + ']' * 2000 + '}'

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


@pytest.mark.parametrize('depth', [1, 2, 31, 32])
def test_ndjson_depth_boundary_accepts_valid_depth(depth):
    line = '{"nested":' + '[' * (depth - 1)
    line += '0' + ']' * (depth - 1) + '}'

    assert isinstance(parse_ndjson_line(line), dict)


@pytest.mark.parametrize('depth', [33, 64, 100, 2000])
def test_ndjson_depth_boundary_rejects_invalid_depth(depth):
    line = '{"nested":' + '[' * (depth - 1)
    line += '0' + ']' * (depth - 1) + '}'

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


@pytest.mark.parametrize(
    'content',
    [
        '[' * 2000,
        '{' * 2000,
        ']' * 2000,
        '}' * 2000,
        '{"example": [1, 2, 3]}',
        'print("Hello")',
        '\\' * 100,
        '"' * 100,
        '\\"' * 100,
    ],
)
def test_ndjson_depth_ignores_string_content(content):
    data = {'message': {'content': content}}

    assert parse_ndjson_line(json.dumps(data)) == data


def test_ndjson_depth_rejects_nested_objects():
    line = '{"nested":' * 33 + '0' + '}' * 33

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


def test_ndjson_depth_rejects_mixed_containers():
    line = '{"nested":[' * 17 + '0' + ']}' * 17

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


def test_ndjson_depth_rejects_unexpected_closing():
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line('}')


def test_ndjson_depth_preserves_escaped_quotes():
    data = {
        'message': {
            'content': 'Example: \\"' + '[' * 100,
        },
    }

    assert parse_ndjson_line(json.dumps(data)) == data


@pytest.mark.parametrize(
    'size',
    [262143, 262144],
)
def test_ndjson_size_boundary_accepts_valid_size(size):
    content = 'a' * (size - 8)
    line = json.dumps(
        {'x': content},
        separators=(',', ':'),
    )

    assert len(line.encode('utf-8')) == size
    assert parse_ndjson_line(line) == {'x': content}


@pytest.mark.parametrize(
    'size',
    [262145, 524288],
)
def test_ndjson_size_boundary_rejects_oversized_line(size):
    line = ' ' * size

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


def test_ndjson_size_accepts_exact_unicode_limit():
    content = '🚀' * 65534

    line = json.dumps(
        {'x': content},
        ensure_ascii=False,
        separators=(',', ':'),
    )

    assert len(line.encode('utf-8')) == 262144
    assert parse_ndjson_line(line) == {'x': content}


def test_ndjson_size_rejects_oversized_unicode_line():
    content = '🚀' * 65535

    line = json.dumps(
        {'x': content},
        ensure_ascii=False,
        separators=(',', ':'),
    )

    assert len(line) < 262144
    assert len(line.encode('utf-8')) > 262144

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


def test_ndjson_size_rejects_invalid_unicode():
    line = '{"content":"' + chr(0xD800) + '"}'

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        parse_ndjson_line(line)

    assert exc_info.value.__suppress_context__ is True


@pytest.mark.parametrize(
    'line',
    [
        '{"done":false,"done":true}',
        '{"done":true,"done":true}',
        '{"x":1,"x":2}',
        '{"message":{"content":"a","content":"b"}}',
        '{"message":{"role":"user","role":"assistant"}}',
        '{"items":[{"x":1,"x":2}]}',
        r'{"done":false,"\u0064one":true}',
        '{"usage":{"input":1,"input":2}}',
    ],
)
def test_ndjson_duplicate_keys_rejected(line):
    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ):
        parse_ndjson_line(line)


def test_ndjson_duplicate_keys_allowed_in_separate_objects():
    data = {
        'first': {'value': 1},
        'second': {'value': 2},
    }

    assert parse_ndjson_line(json.dumps(data)) == data


def test_ndjson_duplicate_keys_inside_strings_are_preserved():
    data = {
        'message': {
            'content': '{"x":1,"x":2}',
        },
    }

    assert parse_ndjson_line(json.dumps(data)) == data


def test_ndjson_duplicate_keys_error_is_sanitized():
    secret = 'fake-sensitive-key'
    line = '{"' + secret + '":1,"' + secret + '":2}'

    with pytest.raises(
        ProviderError,
        match='INVALID_PROVIDER_RESPONSE',
    ) as exc_info:
        parse_ndjson_line(line)

    assert secret not in str(exc_info.value)


def test_ndjson_size_accepts_whitespace_at_limit():
    assert parse_ndjson_line(' ' * 262144) is None
