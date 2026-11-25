import pytest
from pydantic_settings import SettingsConfigDict

from app.core.settings import Settings
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.services.chat_context import (
    ChatContext,
    ChatContextError,
)
from app.services.providers.base import ProviderRole


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_CONTEXT_TEST_',
    )


@pytest.fixture
def settings():
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://fake:fake@localhost/fake',
        JWT_SECRET_KEY='fake-test-secret',
    )


def make_message(
    message_id,
    content,
    *,
    role=ChatMessageRole.USER,
    status=ChatMessageStatus.COMPLETED,
    active=True,
    conversation_id=1,
    reply_to=None,
):
    return ChatMessage(
        id=message_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        status=status,
        is_active=active,
        reply_to_message_id=reply_to,
    )


def make_reply(message_id, reply_to, content, **kwargs):
    return make_message(
        message_id,
        content,
        role=ChatMessageRole.ASSISTANT,
        reply_to=reply_to,
        **kwargs,
    )


def test_build_context_without_history(settings):
    current = make_message(1, 'Como configurar o PostgreSQL?')

    request = ChatContext(settings).build(
        current_message=current,
        history=[],
    )

    assert len(request.messages) == 2
    assert request.messages[0].role is ProviderRole.SYSTEM
    assert request.messages[-1].role is ProviderRole.USER
    assert request.messages[-1].content == current.content


def test_context_preserves_active_turns(settings):
    current = make_message(6, 'Pergunta atual')

    history = [
        make_reply(5, 3, 'Resposta regenerada'),
        make_message(1, 'Primeira pergunta'),
        make_reply(2, 1, 'Primeira resposta'),
        make_message(3, 'Segunda pergunta'),
        make_reply(4, 3, 'Resposta antiga', active=False),
        current,
        make_reply(
            7,
            6,
            '',
            status=ChatMessageStatus.PENDING,
            active=False,
        ),
    ]

    request = ChatContext(settings).build(
        current_message=current,
        history=history,
    )

    assert [message.content for message in request.messages[1:]] == [
        'Primeira pergunta',
        'Primeira resposta',
        'Segunda pergunta',
        'Resposta regenerada',
        'Pergunta atual',
    ]


def test_context_rejects_foreign_conversation(settings):
    current = make_message(2, 'Pergunta atual')

    foreign = make_message(
        1,
        'Outra conversa',
        conversation_id=2,
    )

    with pytest.raises(
        ChatContextError,
        match='another conversation',
    ):
        ChatContext(settings).build(
            current_message=current,
            history=[foreign],
        )


def test_context_limits_history(settings):
    settings = settings.model_copy(
        update={'CHAT_MAX_CONTEXT_MESSAGES': 2},
    )

    current = make_message(5, 'Pergunta atual')

    history = [
        make_message(1, 'Pergunta antiga'),
        make_reply(2, 1, 'Resposta antiga'),
        make_message(3, 'Pergunta recente'),
        make_reply(4, 3, 'Resposta recente'),
    ]

    request = ChatContext(settings).build(
        current_message=current,
        history=history,
    )

    assert [message.content for message in request.messages[1:]] == [
        'Pergunta recente',
        'Resposta recente',
        'Pergunta atual',
    ]


def test_context_removes_oversized_history(settings):
    current = make_message(3, 'Pergunta atual')

    history = [
        make_message(1, 'a' * 4000),
        make_reply(2, 1, 'Resposta antiga'),
    ]

    request = ChatContext(settings).build(
        current_message=current,
        history=history,
    )

    assert len(request.messages) == 2
    assert request.messages[-1].content == current.content


def test_context_rejects_oversized_current_message(settings):
    current = make_message(1, 'a' * 8000)

    with pytest.raises(
        ChatContextError,
        match='context budget',
    ):
        ChatContext(settings).build(
            current_message=current,
            history=[],
        )
