from collections.abc import AsyncIterator
from dataclasses import FrozenInstanceError
from typing import override

import pytest

from app.services.providers import (
    AIProvider,
    ProviderCompletion,
    ProviderDelta,
    ProviderEvent,
    ProviderFinishReason,
    ProviderMessage,
    ProviderRequest,
    ProviderRole,
    ProviderUsage,
)


@pytest.fixture
def user_message():
    return ProviderMessage(
        role=ProviderRole.USER,
        content='Como configurar o PostgreSQL?',
    )


@pytest.fixture
def provider_request(user_message):
    return ProviderRequest(messages=(user_message,))


class FakeProvider(AIProvider):
    @property
    def model(self) -> str:
        return 'fake-model'

    @override
    async def stream(
        self,
        request: ProviderRequest,
    ) -> AsyncIterator[ProviderEvent]:
        yield ProviderDelta(content='Resposta: ')
        yield ProviderDelta(content=request.messages[-1].content)
        yield ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(
                input_tokens=10,
                output_tokens=5,
            ),
        )


def test_provider_role_values():
    assert {role.value for role in ProviderRole} == {
        'system',
        'user',
        'assistant',
    }


def test_provider_finish_reason_values():
    assert {reason.value for reason in ProviderFinishReason} == {
        'stop',
        'length',
    }


@pytest.mark.parametrize('role', list(ProviderRole))
def test_provider_message_valid_roles(role):
    message = ProviderMessage(
        role=role,
        content='Valid content',
    )

    assert message.role == role
    assert message.content == 'Valid content'


@pytest.mark.parametrize(
    'role',
    ['user', 'admin', 'tool', None, 1],
)
def test_provider_message_invalid_role(role):
    with pytest.raises(ValueError, match='Invalid provider'):
        ProviderMessage(role=role, content='Valid content')


@pytest.mark.parametrize(
    'content',
    ['', ' ', '\n\t', None, 123, 'invalid\x00content'],
)
def test_provider_message_invalid_content(content):
    with pytest.raises(ValueError, match='Message content'):
        ProviderMessage(
            role=ProviderRole.USER,
            content=content,
        )


def test_provider_message_preserves_content():
    content = '  Texto\n\n```python\nprint(1)\n```\n'

    message = ProviderMessage(
        role=ProviderRole.ASSISTANT,
        content=content,
    )

    assert message.content == content


def test_provider_message_is_immutable(user_message):
    with pytest.raises(FrozenInstanceError):
        user_message.content = 'Modified'


def test_provider_request_single_message(provider_request):
    assert len(provider_request.messages) == 1
    assert provider_request.messages[0].role == ProviderRole.USER


def test_provider_request_complete_context(user_message):
    messages = (
        ProviderMessage(
            role=ProviderRole.SYSTEM,
            content='System instructions',
        ),
        ProviderMessage(
            role=ProviderRole.USER,
            content='Previous question',
        ),
        ProviderMessage(
            role=ProviderRole.ASSISTANT,
            content='Previous answer',
        ),
        user_message,
    )

    request = ProviderRequest(messages=messages)

    assert request.messages == messages


@pytest.mark.parametrize(
    'messages',
    [(), [], None, ('invalid',), (None,)],
)
def test_provider_request_invalid_messages(messages):
    with pytest.raises(
        ValueError,
        match=(
            'Messages must be a tuple'
            '|At least one message is required'
            '|Invalid provider message'
        ),
    ):
        ProviderRequest(messages=messages)


@pytest.mark.parametrize(
    'role',
    [ProviderRole.SYSTEM, ProviderRole.ASSISTANT],
)
def test_provider_request_invalid_last_role(role):
    message = ProviderMessage(
        role=role,
        content='Content',
    )

    with pytest.raises(ValueError, match='last message'):
        ProviderRequest(messages=(message,))


def test_provider_request_rejects_system_in_history(
    user_message,
):
    system = ProviderMessage(
        role=ProviderRole.SYSTEM,
        content='System instructions',
    )

    with pytest.raises(ValueError, match='first message'):
        ProviderRequest(
            messages=(user_message, system, user_message),
        )


def test_provider_request_rejects_multiple_system_messages(
    user_message,
):
    system = ProviderMessage(
        role=ProviderRole.SYSTEM,
        content='System instructions',
    )

    with pytest.raises(ValueError, match='first message'):
        ProviderRequest(
            messages=(system, system, user_message),
        )


def test_provider_request_is_immutable(provider_request):
    with pytest.raises(FrozenInstanceError):
        provider_request.messages = ()


@pytest.mark.parametrize(
    ('input_tokens', 'output_tokens'),
    [
        (None, None),
        (0, 0),
        (100, 50),
        (100, None),
        (None, 50),
    ],
)
def test_provider_usage_valid_counts(
    input_tokens,
    output_tokens,
):
    usage = ProviderUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    assert usage.input_tokens == input_tokens
    assert usage.output_tokens == output_tokens


@pytest.mark.parametrize(
    'value',
    [-1, True, False, 1.5, '10'],
)
@pytest.mark.parametrize(
    'field',
    ['input_tokens', 'output_tokens'],
)
def test_provider_usage_invalid_counts(field, value):
    with pytest.raises(ValueError, match='Token counts'):
        ProviderUsage(**{field: value})


def test_provider_usage_unknown_defaults():
    usage = ProviderUsage()

    assert usage.input_tokens is None
    assert usage.output_tokens is None


def test_provider_usage_is_immutable():
    usage = ProviderUsage(input_tokens=10)

    with pytest.raises(FrozenInstanceError):
        usage.input_tokens = 20


@pytest.mark.parametrize(
    'content',
    ['Texto', ' ', '\n', '\t', '```python\n'],
)
def test_provider_delta_preserves_content(content):
    delta = ProviderDelta(content=content)

    assert delta.content == content


@pytest.mark.parametrize(
    'content',
    ['', None, 123, 'invalid\x00content'],
)
def test_provider_delta_invalid_content(content):
    with pytest.raises(ValueError, match='Delta content'):
        ProviderDelta(content=content)


def test_provider_delta_is_immutable():
    delta = ProviderDelta(content='Original')

    with pytest.raises(FrozenInstanceError):
        delta.content = 'Modified'


@pytest.mark.parametrize(
    'reason',
    list(ProviderFinishReason),
)
def test_provider_completion_valid_reasons(reason):
    usage = ProviderUsage(
        input_tokens=100,
        output_tokens=50,
    )

    completion = ProviderCompletion(
        finish_reason=reason,
        usage=usage,
    )

    assert completion.finish_reason == reason
    assert completion.usage == usage


@pytest.mark.parametrize(
    'reason',
    ['stop', 'unknown', 'cancelled', None],
)
def test_provider_completion_invalid_reason(reason):
    with pytest.raises(ValueError, match='finish reason'):
        ProviderCompletion(
            finish_reason=reason,
            usage=ProviderUsage(),
        )


@pytest.mark.parametrize(
    'usage',
    [None, {}, 10],
)
def test_provider_completion_invalid_usage(usage):
    with pytest.raises(ValueError, match='Invalid provider usage'):
        ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=usage,
        )


def test_provider_completion_is_immutable():
    completion = ProviderCompletion(
        finish_reason=ProviderFinishReason.STOP,
        usage=ProviderUsage(),
    )

    with pytest.raises(FrozenInstanceError):
        completion.finish_reason = ProviderFinishReason.LENGTH


def test_ai_provider_is_abstract():
    with pytest.raises(TypeError):
        AIProvider()


def test_ai_provider_incomplete_implementation():
    class IncompleteProvider(AIProvider):
        @property
        def model(self) -> str:
            return 'incomplete'

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_fake_provider_model():
    provider = FakeProvider()

    assert isinstance(provider, AIProvider)
    assert provider.model == 'fake-model'


async def test_fake_provider_stream(provider_request):
    provider = FakeProvider()

    events = [event async for event in provider.stream(provider_request)]

    assert len(events) == 3
    assert isinstance(events[0], ProviderDelta)
    assert isinstance(events[1], ProviderDelta)
    assert isinstance(events[2], ProviderCompletion)

    assert events[0].content == 'Resposta: '
    assert events[1].content == (provider_request.messages[-1].content)

    assert events[2].finish_reason == ProviderFinishReason.STOP
    assert events[2].usage.input_tokens == 10
    assert events[2].usage.output_tokens == 5


async def test_fake_provider_reconstruct_response(
    provider_request,
):
    provider = FakeProvider()
    fragments = []

    async for event in provider.stream(provider_request):
        if isinstance(event, ProviderDelta):
            fragments.append(event.content)

    assert ''.join(fragments) == ('Resposta: Como configurar o PostgreSQL?')


async def test_fake_provider_repeated_requests(
    provider_request,
):
    provider = FakeProvider()

    first = [event async for event in provider.stream(provider_request)]

    second = [event async for event in provider.stream(provider_request)]

    assert first == second
