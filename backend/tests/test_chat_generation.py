import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_settings import SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.chat_conversation import (
    ChatConversation,
    ChatGenerationStatus,
)
from app.models.chat_generation_attempt import (
    ChatGenerationAttempt,
    ChatGenerationAttemptStatus,
)
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.schemas.chat import (
    ChatCancellationRequest,
    ChatMessageCreate,
    ChatStreamErrorCode,
)
from app.services import chat_generation_stream
from app.services.chat_errors import (
    ChatConversationNotFoundError,
    ChatGenerationConflictError,
    ChatRegenerationConflictError,
)
from app.services.chat_generation import PreparedGeneration
from app.services.chat_service import ChatService
from app.services.providers.base import (
    AIProvider,
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
        env_prefix='SMARTDESK_GENERATION_TEST_',
    )


@pytest.fixture
def settings():
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://test:test@localhost/test',
        JWT_SECRET_KEY='test-secret',
    )


@pytest.fixture
def session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    query_result = MagicMock()
    query_result.one_or_none.return_value = (None,)
    session.execute.return_value = query_result
    return session


@pytest.fixture
def provider():
    provider = MagicMock(spec=AIProvider)
    provider.model = 'qwen2.5:7b'
    return provider


@pytest.fixture
def service(session, settings, provider, monkeypatch):
    service = ChatService(session, settings, provider)

    monkeypatch.setattr(
        service._generation._reservations,
        'recover_expired_generations',
        AsyncMock(return_value=0),
    )

    return service


@pytest.fixture
def prepared():
    return PreparedGeneration(
        user_id=1,
        conversation_id=1,
        generation_id=uuid4(),
        user_message_id=10,
        assistant_message_id=11,
        request=ProviderRequest(
            messages=(
                ProviderMessage(
                    role=ProviderRole.USER,
                    content='Como configurar o PostgreSQL?',
                ),
            ),
        ),
        expires_at=datetime.now(UTC) + timedelta(seconds=120),
    )


@pytest.fixture
def persistence(session, prepared, provider):
    now = datetime.now(UTC)

    conversation = ChatConversation(
        id=prepared.conversation_id,
        user_id=prepared.user_id,
        title='Suporte PostgreSQL',
        generation_status=ChatGenerationStatus.GENERATING,
        generation_id=prepared.generation_id,
        generation_started_at=now,
        generation_expires_at=prepared.expires_at,
    )

    message = ChatMessage(
        id=prepared.assistant_message_id,
        conversation_id=prepared.conversation_id,
        role=ChatMessageRole.ASSISTANT,
        content='',
        status=ChatMessageStatus.PENDING,
        model=provider.model,
        generation_id=prepared.generation_id,
        reply_to_message_id=prepared.user_message_id,
        is_active=False,
        created_at=now,
    )

    attempt = ChatGenerationAttempt(
        generation_id=prepared.generation_id,
        user_id=prepared.user_id,
        usage_date=now.date(),
        status=ChatGenerationAttemptStatus.RUNNING,
        model=provider.model,
        reserved_at=now,
        expires_at=prepared.expires_at,
    )

    session.scalar.side_effect = [
        conversation,
        message,
        attempt,
        1,
    ]

    return conversation, message, attempt


async def collect_events(service, prepared):
    return [event async for event in service.stream_generation(prepared)]


@pytest.mark.parametrize(
    ('finish_reason', 'expected_status', 'terminal_type'),
    [
        (
            ProviderFinishReason.STOP,
            ChatMessageStatus.COMPLETED,
            'response.completed',
        ),
        (
            ProviderFinishReason.LENGTH,
            ChatMessageStatus.TRUNCATED,
            'response.truncated',
        ),
    ],
)
async def test_generation_success(
    service,
    session,
    provider,
    prepared,
    persistence,
    finish_reason,
    expected_status,
    terminal_type,
):
    async def stream(request):
        assert request == prepared.request

        yield ProviderDelta(content='Configure')
        yield ProviderDelta(content=' o PostgreSQL.')

        yield ProviderCompletion(
            finish_reason=finish_reason,
            usage=ProviderUsage(
                input_tokens=100,
                output_tokens=20,
            ),
        )

    provider.stream.side_effect = stream

    events = await collect_events(service, prepared)

    assert [event.type for event in events] == [
        'message.created',
        'response.delta',
        'response.delta',
        terminal_type,
    ]

    conversation, message, attempt = persistence

    assert message.content == 'Configure o PostgreSQL.'
    assert message.status == expected_status
    assert message.input_tokens == 100
    assert message.output_tokens == 20
    assert message.is_active == (
        expected_status == ChatMessageStatus.COMPLETED
    )

    assert attempt.status.value == expected_status.value
    assert conversation.generation_status == ChatGenerationStatus.IDLE
    assert conversation.generation_id is None

    assert events[-1].message.content == message.content

    session.commit.assert_awaited_once()


async def test_generation_preserves_partial_response(
    service,
    session,
    provider,
    prepared,
    persistence,
):
    async def stream(request):
        yield ProviderDelta(content='Resposta parcial')

        raise ProviderError(
            ProviderErrorCode.STREAM_INTERRUPTED,
        )

    provider.stream.side_effect = stream

    events = await collect_events(service, prepared)

    assert events[-1].type == 'response.failed'
    assert events[-1].error_code == (ChatStreamErrorCode.STREAM_INTERRUPTED)

    conversation, message, attempt = persistence

    assert message.content == 'Resposta parcial'
    assert message.status == ChatMessageStatus.FAILED
    assert message.is_active is False
    assert message.input_tokens is None
    assert message.output_tokens is None
    assert attempt.error_code == 'STREAM_INTERRUPTED'
    assert conversation.generation_id is None

    session.commit.assert_awaited_once()


async def test_generation_expired_before_stream(
    service,
    provider,
    prepared,
    persistence,
):
    expired = replace(
        prepared,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    async def stream(request):
        yield ProviderDelta(content='Unexpected response')

    provider.stream.side_effect = stream

    events = await collect_events(service, expired)

    assert events[-1].type == 'response.failed'
    assert events[-1].error_code == (ChatStreamErrorCode.GENERATION_TIMEOUT)

    assert not persistence[1].content
    assert persistence[1].status == ChatMessageStatus.FAILED


async def test_generation_conflict(
    service,
    session,
    provider,
    prepared,
):
    async def stream(request):
        yield ProviderDelta(content='Resposta')

        yield ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        )

    provider.stream.side_effect = stream
    session.scalar.return_value = None

    events = await collect_events(service, prepared)

    assert events[-1].type == 'response.error'
    assert events[-1].error_code == (ChatStreamErrorCode.GENERATION_CONFLICT)

    session.rollback.assert_awaited()
    session.commit.assert_not_awaited()


async def test_generation_commit_failure(
    service,
    session,
    provider,
    prepared,
    persistence,
):
    async def stream(request):
        yield ProviderDelta(content='Resposta')

        yield ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        )

    provider.stream.side_effect = stream
    session.commit.side_effect = RuntimeError('Commit failed.')

    events = await collect_events(service, prepared)

    assert [event.type for event in events] == [
        'message.created',
        'response.delta',
        'response.error',
    ]

    assert events[-1].error_code == (ChatStreamErrorCode.PERSISTENCE_ERROR)

    payload = events[-1].model_dump_json()

    assert 'Commit failed' not in payload
    assert 'message' not in events[-1].model_dump()

    session.rollback.assert_awaited()
    session.commit.assert_awaited_once()


async def test_prepare_generation(
    service,
    session,
    prepared,
):
    generation = service._generation

    generation._reservations.reserve = AsyncMock(
        return_value=prepared.generation_id,
    )

    history = MagicMock()
    history.all.return_value = []
    session.scalars.return_value = history
    session.scalar.return_value = prepared.expires_at

    async def flush():
        for index, call in enumerate(
            session.add.call_args_list,
            start=10,
        ):
            call.args[0].id = index

    session.flush.side_effect = flush

    result = await service.prepare_generation(
        user_id=1,
        conversation_id=1,
        data=ChatMessageCreate(content='Como configurar o PostgreSQL?'),
    )

    assert result.generation_id == prepared.generation_id
    assert result.user_message_id == 10
    assert result.assistant_message_id == 11
    assert result.expires_at == prepared.expires_at
    assert result.request.messages[-1].role == ProviderRole.USER

    user_message, assistant_message = [
        call.args[0] for call in session.add.call_args_list
    ]

    assert user_message.status == ChatMessageStatus.COMPLETED
    assert assistant_message.status == ChatMessageStatus.PENDING
    assert assistant_message.reply_to_message_id == user_message.id

    session.commit.assert_awaited_once()


async def test_prepare_generation_rolls_back(
    service,
    session,
    prepared,
):
    generation = service._generation

    generation._reservations.reserve = AsyncMock(
        return_value=prepared.generation_id,
    )

    session.flush.side_effect = RuntimeError('Flush failed.')

    with pytest.raises(RuntimeError, match='Flush failed'):
        await service.prepare_generation(
            user_id=1,
            conversation_id=1,
            data=ChatMessageCreate(content='Mensagem'),
        )

    session.rollback.assert_awaited()
    session.commit.assert_not_awaited()


async def test_request_generation_cancellation(
    service,
    session,
    prepared,
    persistence,
):
    conversation = persistence[0]
    session.execute.return_value.scalar_one_or_none.return_value = conversation

    response = await service.cancel_generation(
        user_id=prepared.user_id,
        conversation_id=prepared.conversation_id,
        data=ChatCancellationRequest(
            generation_id=prepared.generation_id,
        ),
    )

    assert response.cancellation_requested is True
    assert response.generation_id == prepared.generation_id
    assert conversation.cancel_requested_at is not None

    session.commit.assert_awaited_once()


async def test_repeated_cancellation_preserves_timestamp(
    service,
    session,
    prepared,
    persistence,
):
    conversation = persistence[0]
    requested_at = datetime.now(UTC)
    conversation.cancel_requested_at = requested_at

    session.execute.return_value.scalar_one_or_none.return_value = conversation

    await service.cancel_generation(
        user_id=prepared.user_id,
        conversation_id=prepared.conversation_id,
        data=ChatCancellationRequest(
            generation_id=prepared.generation_id,
        ),
    )

    assert conversation.cancel_requested_at == requested_at


async def test_cancel_stale_generation(
    service,
    session,
    prepared,
    persistence,
):
    session.execute.return_value.scalar_one_or_none.return_value = persistence[
        0
    ]

    with pytest.raises(ChatGenerationConflictError):
        await service.cancel_generation(
            user_id=prepared.user_id,
            conversation_id=prepared.conversation_id,
            data=ChatCancellationRequest(
                generation_id=uuid4(),
            ),
        )

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()


async def test_cancel_inaccessible_conversation(
    service,
    session,
    prepared,
):
    session.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(ChatConversationNotFoundError):
        await service.cancel_generation(
            user_id=2,
            conversation_id=prepared.conversation_id,
            data=ChatCancellationRequest(
                generation_id=prepared.generation_id,
            ),
        )

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()


async def test_cancel_before_provider_consumption(
    service,
    session,
    provider,
    prepared,
    persistence,
):
    async def stream(request):
        pytest.fail('Provider must not be consumed.')
        yield ProviderDelta(content='Unexpected response')

    provider.stream.side_effect = stream

    session.execute.return_value.one_or_none.return_value = (
        datetime.now(UTC),
    )

    events = await collect_events(service, prepared)

    assert [event.type for event in events] == [
        'message.created',
        'response.cancelled',
    ]

    assert persistence[1].status == ChatMessageStatus.CANCELLED
    assert persistence[2].status == ChatGenerationAttemptStatus.CANCELLED
    assert persistence[0].generation_id is None


async def test_cancel_while_waiting_for_provider(
    service,
    session,
    provider,
    prepared,
    persistence,
    monkeypatch,
):

    monkeypatch.setattr(
        chat_generation_stream,
        'CANCELLATION_POLL_SECONDS',
        0.01,
    )

    closed = asyncio.Event()

    async def stream(request):
        try:
            yield ProviderDelta(content='Resposta parcial')
            await asyncio.Event().wait()
        finally:
            closed.set()

    provider.stream.side_effect = stream

    session.execute.return_value.one_or_none.side_effect = [
        (None,),
        (None,),
        (datetime.now(UTC),),
    ]

    events = await asyncio.wait_for(
        collect_events(service, prepared),
        timeout=2,
    )

    assert events[-1].type == 'response.cancelled'
    assert persistence[1].content == 'Resposta parcial'
    assert closed.is_set()
    assert persistence[0].generation_id is None


async def test_cancellation_wins_during_finalization(
    service,
    provider,
    prepared,
    persistence,
):
    persistence[0].cancel_requested_at = datetime.now(UTC)

    async def stream(request):
        yield ProviderDelta(content='Resposta concluída')

        yield ProviderCompletion(
            finish_reason=ProviderFinishReason.STOP,
            usage=ProviderUsage(),
        )

    provider.stream.side_effect = stream

    events = await collect_events(service, prepared)

    assert events[-1].type == 'response.cancelled'
    assert persistence[1].status == ChatMessageStatus.CANCELLED
    assert persistence[1].is_active is False


async def test_disconnect_preserves_partial_response(
    service,
    session,
    provider,
    prepared,
    persistence,
):
    closed = asyncio.Event()

    async def stream(request):
        try:
            yield ProviderDelta(content='Resposta parcial')
            await asyncio.Event().wait()
        finally:
            closed.set()

    provider.stream.side_effect = stream

    events = service.stream_generation(prepared)

    created = await anext(events)
    delta = await anext(events)

    assert created.type == 'message.created'
    assert delta.type == 'response.delta'

    await events.aclose()

    assert closed.is_set()
    assert persistence[1].content == 'Resposta parcial'
    assert persistence[1].status == ChatMessageStatus.CANCELLED
    assert persistence[0].generation_id is None

    session.commit.assert_awaited_once()


@pytest.fixture
def original_response(prepared):
    now = datetime.now(UTC)

    return ChatMessage(
        id=prepared.assistant_message_id + 100,
        conversation_id=prepared.conversation_id,
        role=ChatMessageRole.ASSISTANT,
        status=ChatMessageStatus.COMPLETED,
        content='Resposta original',
        model='qwen2.5:7b',
        generation_id=uuid4(),
        reply_to_message_id=prepared.user_message_id,
        is_active=True,
        created_at=now,
        completed_at=now,
    )


async def test_prepare_regeneration_success(
    service,
    session,
    prepared,
    persistence,
    original_response,
    monkeypatch,
):
    question = ChatMessage(
        id=prepared.user_message_id,
        conversation_id=prepared.conversation_id,
        role=ChatMessageRole.USER,
        status=ChatMessageStatus.COMPLETED,
        content='Como configurar o PostgreSQL?',
        is_active=True,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )

    generation = service._generation

    monkeypatch.setattr(
        generation._reservations,
        'reserve',
        AsyncMock(return_value=prepared.generation_id),
    )

    monkeypatch.setattr(
        generation,
        '_load_history',
        AsyncMock(return_value=[original_response]),
    )

    monkeypatch.setattr(
        generation,
        '_create_assistant_message',
        AsyncMock(return_value=persistence[1]),
    )

    session.scalar.side_effect = [
        original_response,
        question,
        prepared.expires_at,
    ]

    result = await service.prepare_regeneration(
        user_id=prepared.user_id,
        conversation_id=prepared.conversation_id,
        message_id=original_response.id,
    )

    assert result.user_message_id == question.id
    assert result.regenerated_from_id == original_response.id
    assert result.request.messages[-1].content == question.content
    assert original_response.is_active is True

    assert all(
        message.content != original_response.content
        for message in result.request.messages
    )

    assert persistence[1].regenerated_from_id == original_response.id

    session.add.assert_not_called()
    session.commit.assert_awaited_once()


@pytest.mark.parametrize('invalid_target', [True, False])
async def test_prepare_regeneration_invalid_message(
    service,
    session,
    prepared,
    original_response,
    monkeypatch,
    invalid_target,
):
    generation = service._generation

    monkeypatch.setattr(
        generation._reservations,
        'reserve',
        AsyncMock(return_value=prepared.generation_id),
    )

    if invalid_target:
        session.scalar.side_effect = [None]
    else:
        latest_question = MagicMock()
        latest_question.id = prepared.user_message_id + 100

        session.scalar.side_effect = [
            original_response,
            latest_question,
        ]

    with pytest.raises(ChatRegenerationConflictError):
        await service.prepare_regeneration(
            user_id=prepared.user_id,
            conversation_id=prepared.conversation_id,
            message_id=original_response.id,
        )

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.parametrize(
    ('finish_reason', 'expected_event', 'expected_active'),
    [
        (
            ProviderFinishReason.STOP,
            'response.completed',
            True,
        ),
        (
            ProviderFinishReason.LENGTH,
            'response.truncated',
            False,
        ),
    ],
)
async def test_regeneration_response_replacement(
    service,
    session,
    provider,
    prepared,
    persistence,
    original_response,
    finish_reason,
    expected_event,
    expected_active,
):
    regenerated = replace(
        prepared,
        regenerated_from_id=original_response.id,
    )

    persistence[1].regenerated_from_id = original_response.id

    session.scalar.side_effect = [
        *persistence[:3],
        original_response,
    ]

    async def stream(request):
        yield ProviderDelta(content='Nova resposta')

        yield ProviderCompletion(
            finish_reason=finish_reason,
            usage=ProviderUsage(),
        )

    provider.stream.side_effect = stream

    events = await collect_events(service, regenerated)

    assert events[0].regenerated_from_id == original_response.id
    assert events[-1].type == expected_event
    assert persistence[1].is_active is expected_active
    assert original_response.is_active is not expected_active
    assert original_response.content == 'Resposta original'

    session.commit.assert_awaited_once()


async def test_failed_regeneration_preserves_original(
    service,
    session,
    provider,
    prepared,
    persistence,
    original_response,
):
    regenerated = replace(
        prepared,
        regenerated_from_id=original_response.id,
    )

    persistence[1].regenerated_from_id = original_response.id

    async def stream(request):
        yield ProviderDelta(content='Resposta incompleta')

    provider.stream.side_effect = stream

    events = await collect_events(service, regenerated)

    assert events[-1].type == 'response.failed'
    assert original_response.is_active is True
    assert persistence[1].is_active is False
    assert persistence[1].status == ChatMessageStatus.FAILED

    session.commit.assert_awaited_once()


async def test_cancelled_regeneration_preserves_original(
    service,
    session,
    provider,
    prepared,
    persistence,
    original_response,
):
    regenerated = replace(
        prepared,
        regenerated_from_id=original_response.id,
    )

    persistence[1].regenerated_from_id = original_response.id

    session.execute.return_value.one_or_none.return_value = (
        datetime.now(UTC),
    )

    async def stream(request):
        pytest.fail('Cancelled provider must not be consumed.')
        yield ProviderDelta(content='Unexpected response')

    provider.stream.side_effect = stream

    events = await collect_events(service, regenerated)

    assert events[-1].type == 'response.cancelled'
    assert original_response.is_active is True
    assert persistence[1].is_active is False
    assert persistence[1].status == ChatMessageStatus.CANCELLED

    session.commit.assert_awaited_once()


async def test_abort_unstarted_generation(
    service,
    session,
    provider,
    prepared,
    persistence,
):
    await service.abort_unstarted_generation(
        prepared,
    )

    conversation, message, attempt = persistence

    assert message.status == ChatMessageStatus.CANCELLED
    assert not message.content
    assert message.is_active is False

    assert attempt.status == ChatGenerationAttemptStatus.CANCELLED

    assert conversation.generation_status == ChatGenerationStatus.IDLE
    assert conversation.generation_id is None

    provider.stream.assert_not_called()
    session.commit.assert_awaited_once()
