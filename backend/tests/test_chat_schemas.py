from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.chat_conversation import (
    ChatConversation,
    ChatGenerationStatus,
)
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.schemas.chat import (
    ChatCancellationRequest,
    ChatCancellationResponse,
    ChatConversationCreate,
    ChatConversationListResponse,
    ChatConversationPublic,
    ChatConversationUpdate,
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessagePublic,
    ChatStreamEvent,
    ChatUsageResponse,
)


def test_chat_conversation_create_without_title():
    result = ChatConversationCreate()

    assert result.title is None


def test_chat_conversation_create_with_null_title():
    result = ChatConversationCreate(title=None)

    assert result.title is None


def test_chat_conversation_create_with_title():
    result = ChatConversationCreate(
        title='Suporte técnico',
    )

    assert result.title == 'Suporte técnico'


@pytest.mark.parametrize(
    ('title', 'expected'),
    [
        ('  Suporte técnico  ', 'Suporte técnico'),
        ('\tSuporte técnico\n', 'Suporte técnico'),
        ('A', 'A'),
        ('a' * 150, 'a' * 150),
        ('  ' + 'a' * 150 + '  ', 'a' * 150),
    ],
)
def test_chat_conversation_create_normalizes_title(
    title,
    expected,
):
    result = ChatConversationCreate(title=title)

    assert result.title == expected


@pytest.mark.parametrize(
    'title',
    [
        '',
        ' ',
        '   ',
        '\t\n',
        'a' * 151,
        123,
        True,
        [],
        {},
    ],
)
def test_chat_conversation_create_rejects_invalid_title(
    title,
):
    with pytest.raises(ValidationError):
        ChatConversationCreate.model_validate({'title': title})


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('id', 1),
        ('user_id', 2),
        ('role', 'admin'),
        ('model', 'qwen2.5:7b'),
        ('generation_status', 'idle'),
        ('generation_id', None),
        ('generation_started_at', None),
        ('generation_expires_at', None),
        ('cancel_requested_at', None),
        ('created_at', None),
        ('updated_at', None),
        ('messages', []),
        ('unexpected_field', 'value'),
    ],
)
def test_chat_conversation_create_rejects_extra_fields(
    field,
    value,
):
    payload = {
        'title': 'Suporte técnico',
        field: value,
    }

    with pytest.raises(ValidationError) as exc:
        ChatConversationCreate.model_validate(payload)

    assert any(
        error['type'] == 'extra_forbidden' and error['loc'] == (field,)
        for error in exc.value.errors()
    )


def test_chat_conversation_create_serialization():
    result = ChatConversationCreate(
        title='  Suporte técnico  ',
    )

    assert result.model_dump() == {
        'title': 'Suporte técnico',
    }


def test_chat_conversation_update_with_title():
    result = ChatConversationUpdate(
        title='Novo título',
    )

    assert result.title == 'Novo título'


@pytest.mark.parametrize(
    ('title', 'expected'),
    [
        ('  Novo título  ', 'Novo título'),
        ('\tNovo título\n', 'Novo título'),
        ('A', 'A'),
        ('a' * 150, 'a' * 150),
        ('  ' + 'a' * 150 + '  ', 'a' * 150),
    ],
)
def test_chat_conversation_update_normalizes_title(
    title,
    expected,
):
    result = ChatConversationUpdate(title=title)

    assert result.title == expected


def test_chat_conversation_update_requires_title():
    with pytest.raises(ValidationError) as exc:
        ChatConversationUpdate.model_validate({})

    assert any(
        error['type'] == 'missing' and error['loc'] == ('title',)
        for error in exc.value.errors()
    )


@pytest.mark.parametrize(
    'title',
    [
        None,
        '',
        ' ',
        '   ',
        '\t\n',
        'a' * 151,
        123,
        True,
        [],
        {},
    ],
)
def test_chat_conversation_update_rejects_invalid_title(
    title,
):
    with pytest.raises(ValidationError):
        ChatConversationUpdate.model_validate({'title': title})


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('id', 1),
        ('user_id', 2),
        ('role', 'admin'),
        ('model', 'qwen2.5:7b'),
        ('generation_status', 'idle'),
        ('generation_id', None),
        ('generation_started_at', None),
        ('generation_expires_at', None),
        ('cancel_requested_at', None),
        ('created_at', None),
        ('updated_at', None),
        ('messages', []),
        ('unexpected_field', 'value'),
    ],
)
def test_chat_conversation_update_rejects_extra_fields(
    field,
    value,
):
    payload = {
        'title': 'Novo título',
        field: value,
    }

    with pytest.raises(ValidationError) as exc:
        ChatConversationUpdate.model_validate(payload)

    assert any(
        error['type'] == 'extra_forbidden' and error['loc'] == (field,)
        for error in exc.value.errors()
    )


def test_chat_conversation_update_serialization():
    result = ChatConversationUpdate(
        title='  Novo título  ',
    )

    assert result.model_dump() == {
        'title': 'Novo título',
    }


def test_chat_conversation_update_json_schema():
    schema = ChatConversationUpdate.model_json_schema()

    assert schema['additionalProperties'] is False
    assert schema['required'] == ['title']
    assert set(schema['properties']) == {'title'}

    title = schema['properties']['title']

    assert title['type'] == 'string'
    assert title['minLength'] == 1
    assert title['maxLength'] == 150


@pytest.fixture
def conversation_public_data():
    return {
        'id': 1,
        'title': 'Suporte técnico',
        'generation_status': 'idle',
        'generation_id': None,
        'created_at': datetime(2026, 11, 25, tzinfo=UTC),
        'updated_at': datetime(2026, 11, 25, tzinfo=UTC),
    }


def test_chat_conversation_public_valid(
    conversation_public_data,
):
    result = ChatConversationPublic.model_validate(conversation_public_data)

    assert result.id == 1
    assert result.title == 'Suporte técnico'
    assert result.generation_status == ChatGenerationStatus.IDLE
    assert result.generation_id is None


def test_chat_conversation_public_from_orm(
    conversation_public_data,
):
    conversation = ChatConversation(
        **conversation_public_data,
        user_id=2,
    )

    result = ChatConversationPublic.model_validate(conversation)

    assert result.id == conversation.id
    assert result.title == conversation.title
    assert result.created_at == conversation.created_at


def test_chat_conversation_public_generating(
    conversation_public_data,
):
    generation_id = uuid4()

    conversation_public_data.update(
        generation_status='generating',
        generation_id=generation_id,
    )

    result = ChatConversationPublic.model_validate(conversation_public_data)

    assert result.generation_status == ChatGenerationStatus.GENERATING
    assert result.generation_id == generation_id


def test_chat_conversation_public_uuid_serialization(
    conversation_public_data,
):
    generation_id = uuid4()

    conversation_public_data.update(
        generation_status='generating',
        generation_id=str(generation_id),
    )

    result = ChatConversationPublic.model_validate(conversation_public_data)

    assert isinstance(result.generation_id, UUID)
    assert result.model_dump(mode='json')['generation_id'] == str(
        generation_id
    )


@pytest.mark.parametrize(
    'invalid_id',
    [0, -1, None, True, '1', 1.5],
)
def test_chat_conversation_public_rejects_invalid_id(
    conversation_public_data,
    invalid_id,
):
    conversation_public_data['id'] = invalid_id

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


@pytest.mark.parametrize(
    'title',
    ['', '   ', 'a' * 151, None, 123],
)
def test_chat_conversation_public_rejects_invalid_title(
    conversation_public_data,
    title,
):
    conversation_public_data['title'] = title

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


@pytest.mark.parametrize(
    'status',
    ['invalid', 'completed', 'pending', None],
)
def test_chat_conversation_public_rejects_invalid_status(
    conversation_public_data,
    status,
):
    conversation_public_data['generation_status'] = status

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


def test_chat_conversation_public_rejects_idle_with_uuid(
    conversation_public_data,
):
    conversation_public_data['generation_id'] = uuid4()

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


def test_chat_conversation_public_rejects_generating_without_uuid(
    conversation_public_data,
):
    conversation_public_data['generation_status'] = 'generating'

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


def test_chat_conversation_public_rejects_invalid_uuid(
    conversation_public_data,
):
    conversation_public_data.update(
        generation_status='generating',
        generation_id='invalid-uuid',
    )

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


@pytest.mark.parametrize(
    'field',
    ['created_at', 'updated_at'],
)
def test_chat_conversation_public_requires_timezone(
    conversation_public_data,
    field,
):
    conversation_public_data[field] = datetime(2026, 11, 25)

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


@pytest.mark.parametrize(
    'field',
    [
        'id',
        'title',
        'generation_status',
        'generation_id',
        'created_at',
        'updated_at',
    ],
)
def test_chat_conversation_public_requires_fields(
    conversation_public_data,
    field,
):
    conversation_public_data.pop(field)

    with pytest.raises(ValidationError):
        ChatConversationPublic.model_validate(conversation_public_data)


def test_chat_conversation_public_excludes_internal_fields(
    conversation_public_data,
):
    conversation = ChatConversation(
        **conversation_public_data,
        user_id=2,
    )

    result = ChatConversationPublic.model_validate(conversation)

    assert set(result.model_dump()) == {
        'id',
        'title',
        'generation_status',
        'generation_id',
        'created_at',
        'updated_at',
    }


def test_chat_conversation_public_json_serialization(
    conversation_public_data,
):
    result = ChatConversationPublic.model_validate(conversation_public_data)

    payload = result.model_dump(mode='json')

    assert payload['generation_status'] == 'idle'
    assert payload['generation_id'] is None
    assert payload['created_at'] == '2026-11-25T00:00:00Z'
    assert payload['updated_at'] == '2026-11-25T00:00:00Z'


def test_chat_conversation_public_json_schema():
    schema = ChatConversationPublic.model_json_schema()

    expected = {
        'id',
        'title',
        'generation_status',
        'generation_id',
        'created_at',
        'updated_at',
    }

    assert set(schema['properties']) == expected
    assert set(schema['required']) == expected
    assert schema['properties']['id']['exclusiveMinimum'] == 0
    assert schema['properties']['created_at']['format'] == 'date-time'
    assert schema['properties']['updated_at']['format'] == 'date-time'


@pytest.fixture
def conversation_list_data(conversation_public_data):
    return {
        'items': [conversation_public_data],
        'total': 1,
        'page': 1,
        'page_size': 20,
        'pages': 1,
    }


def test_chat_conversation_list_valid(
    conversation_list_data,
):
    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    assert result.total == 1
    assert result.page == 1
    assert result.page_size == 20
    assert result.pages == 1
    assert len(result.items) == 1
    assert isinstance(
        result.items[0],
        ChatConversationPublic,
    )


def test_chat_conversation_list_empty(
    conversation_list_data,
):
    conversation_list_data.update(
        items=[],
        total=0,
        pages=0,
    )

    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    assert result.items == []
    assert result.total == 0
    assert result.pages == 0


@pytest.mark.parametrize(
    ('total', 'page_size', 'pages'),
    [
        (1, 20, 1),
        (20, 20, 1),
        (21, 20, 2),
        (40, 20, 2),
        (41, 20, 3),
        (100, 100, 1),
        (101, 100, 2),
        (1, 1, 1),
    ],
)
def test_chat_conversation_list_page_calculation(
    conversation_list_data,
    total,
    page_size,
    pages,
):
    conversation_list_data.update(
        total=total,
        page_size=page_size,
        pages=pages,
    )

    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    assert result.pages == pages


def test_chat_conversation_list_last_page(
    conversation_list_data,
):
    conversation_list_data.update(
        total=41,
        page=3,
        page_size=20,
        pages=3,
    )

    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    assert result.page == 3
    assert len(result.items) == 1


def test_chat_conversation_list_out_of_range(
    conversation_list_data,
):
    conversation_list_data.update(
        items=[],
        total=1,
        page=2,
        pages=1,
    )

    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    assert result.items == []
    assert result.page == 2


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('total', -1),
        ('total', True),
        ('total', '1'),
        ('page', 0),
        ('page', -1),
        ('page', True),
        ('page', '1'),
        ('page_size', 0),
        ('page_size', 101),
        ('page_size', True),
        ('page_size', '20'),
        ('pages', -1),
        ('pages', True),
        ('pages', '1'),
    ],
)
def test_chat_conversation_list_rejects_invalid_metadata(
    conversation_list_data,
    field,
    value,
):
    conversation_list_data[field] = value

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


@pytest.mark.parametrize(
    'pages',
    [0, 2, 3],
)
def test_chat_conversation_list_rejects_wrong_pages(
    conversation_list_data,
    pages,
):
    conversation_list_data['pages'] = pages

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


def test_chat_conversation_list_rejects_too_many_items(
    conversation_list_data,
):
    conversation_list_data['items'] *= 2

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


def test_chat_conversation_list_rejects_last_page_overflow(
    conversation_list_data,
):
    conversation_list_data.update(
        total=21,
        page=2,
        page_size=20,
        pages=2,
    )

    conversation_list_data['items'] *= 2

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


def test_chat_conversation_list_rejects_out_of_range_items(
    conversation_list_data,
):
    conversation_list_data['page'] = 2

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


def test_chat_conversation_list_rejects_invalid_item(
    conversation_list_data,
):
    conversation_list_data['items'][0]['id'] = 0

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


@pytest.mark.parametrize(
    'field',
    ['items', 'total', 'page', 'page_size', 'pages'],
)
def test_chat_conversation_list_requires_fields(
    conversation_list_data,
    field,
):
    conversation_list_data.pop(field)

    with pytest.raises(ValidationError):
        ChatConversationListResponse.model_validate(conversation_list_data)


def test_chat_conversation_list_excludes_internal_fields(
    conversation_list_data,
):
    conversation_list_data['items'][0]['user_id'] = 2

    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    payload = result.model_dump(mode='json')

    assert 'user_id' not in payload['items'][0]
    assert len(payload['items'][0]) == 6


def test_chat_conversation_list_json_serialization(
    conversation_list_data,
):
    result = ChatConversationListResponse.model_validate(
        conversation_list_data
    )

    payload = result.model_dump(mode='json')

    assert payload['total'] == 1
    assert payload['page'] == 1
    assert payload['page_size'] == 20
    assert payload['pages'] == 1
    assert payload['items'][0]['generation_status'] == 'idle'


def test_chat_conversation_list_json_schema():
    schema = ChatConversationListResponse.model_json_schema()

    expected = {
        'items',
        'total',
        'page',
        'page_size',
        'pages',
    }

    assert set(schema['properties']) == expected
    assert set(schema['required']) == expected

    properties = schema['properties']

    assert properties['total']['minimum'] == 0
    assert properties['page']['minimum'] == 1
    assert properties['page_size']['minimum'] == 1
    assert properties['page_size']['maximum'] == 100
    assert properties['pages']['minimum'] == 0

    assert properties['items']['type'] == 'array'
    assert properties['items']['items']['$ref'] == (
        '#/$defs/ChatConversationPublic'
    )


def test_chat_message_create_valid():
    result = ChatMessageCreate(
        content='Como configurar o PostgreSQL?',
    )

    assert result.content == 'Como configurar o PostgreSQL?'


@pytest.mark.parametrize(
    ('content', 'expected'),
    [
        ('  Suporte técnico  ', 'Suporte técnico'),
        ('\tSuporte técnico\n', 'Suporte técnico'),
        ('A', 'A'),
        ('a' * 8000, 'a' * 8000),
        ('  ' + 'a' * 8000 + '  ', 'a' * 8000),
        ('Olá, preciso de ajuda! 🚀', 'Olá, preciso de ajuda! 🚀'),
        ('á' * 8000, 'á' * 8000),
    ],
)
def test_chat_message_create_normalizes_content(
    content,
    expected,
):
    result = ChatMessageCreate(content=content)

    assert result.content == expected


@pytest.mark.parametrize(
    'content',
    [
        'Linha 1\nLinha 2',
        'def main():\n    return True',
        '**Erro:** conexão recusada.',
        'SELECT * FROM tickets;',
        '<div>Exemplo HTML</div>',
        'Caminho: /var/log/postgresql/',
    ],
)
def test_chat_message_create_preserves_technical_content(
    content,
):
    result = ChatMessageCreate(content=content)

    assert result.content == content


def test_chat_message_create_requires_content():
    with pytest.raises(ValidationError) as exc:
        ChatMessageCreate.model_validate({})

    assert any(
        error['type'] == 'missing' and error['loc'] == ('content',)
        for error in exc.value.errors()
    )


@pytest.mark.parametrize(
    'content',
    [
        None,
        '',
        ' ',
        '   ',
        '\t\n',
        'a' * 8001,
        'á' * 8001,
        123,
        1.5,
        True,
        [],
        {},
        b'hello',
    ],
)
def test_chat_message_create_rejects_invalid_content(
    content,
):
    with pytest.raises(ValidationError):
        ChatMessageCreate.model_validate({'content': content})


@pytest.mark.parametrize(
    'content',
    [
        '\x00',
        'hello\x00world',
        '\x00hello',
        'hello\x00',
    ],
)
def test_chat_message_create_rejects_null_characters(
    content,
):
    with pytest.raises(ValidationError) as exc:
        ChatMessageCreate(content=content)

    assert any(
        error['loc'] == ('content',) and 'null characters' in error['msg']
        for error in exc.value.errors()
    )


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('id', 1),
        ('conversation_id', 2),
        ('user_id', 3),
        ('role', 'assistant'),
        ('status', 'completed'),
        ('model', 'qwen2.5:7b'),
        ('generation_id', None),
        ('input_tokens', 100),
        ('output_tokens', 200),
        ('reply_to_message_id', 1),
        ('regenerated_from_id', 1),
        ('is_active', True),
        ('created_at', None),
        ('completed_at', None),
        ('system_prompt', 'Custom instructions'),
        ('temperature', 1.0),
        ('max_tokens', 10000),
        ('unexpected_field', 'value'),
    ],
)
def test_chat_message_create_rejects_extra_fields(
    field,
    value,
):
    payload = {
        'content': 'Preciso de ajuda técnica.',
        field: value,
    }

    with pytest.raises(ValidationError) as exc:
        ChatMessageCreate.model_validate(payload)

    assert any(
        error['type'] == 'extra_forbidden' and error['loc'] == (field,)
        for error in exc.value.errors()
    )


def test_chat_message_create_serialization():
    result = ChatMessageCreate(
        content='  Preciso de ajuda técnica.  ',
    )

    assert result.model_dump() == {
        'content': 'Preciso de ajuda técnica.',
    }


def test_chat_message_create_json_round_trip():
    original = ChatMessageCreate(
        content='Olá! Como configurar o Docker?',
    )

    restored = ChatMessageCreate.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original


def test_chat_message_create_json_schema():
    schema = ChatMessageCreate.model_json_schema()

    assert schema['additionalProperties'] is False
    assert schema['required'] == ['content']
    assert set(schema['properties']) == {'content'}

    content = schema['properties']['content']

    assert content['type'] == 'string'
    assert content['minLength'] == 1
    assert content['maxLength'] == 8000


@pytest.fixture
def message_public_data():

    now = datetime.now(UTC)

    return {
        'id': 1,
        'conversation_id': 1,
        'role': 'user',
        'content': 'Como configurar o PostgreSQL?',
        'status': 'completed',
        'model': None,
        'generation_id': None,
        'input_tokens': None,
        'output_tokens': None,
        'reply_to_message_id': None,
        'regenerated_from_id': None,
        'is_active': True,
        'created_at': now,
        'completed_at': now,
    }


@pytest.fixture
def assistant_message_data(message_public_data):

    return {
        **message_public_data,
        'id': 2,
        'role': 'assistant',
        'content': 'Verifique o serviço do PostgreSQL.',
        'model': 'qwen2.5:7b',
        'generation_id': uuid4(),
        'input_tokens': 100,
        'output_tokens': 50,
        'reply_to_message_id': 1,
    }


def test_chat_message_public_user(message_public_data):
    result = ChatMessagePublic.model_validate(message_public_data)

    assert result.role.value == 'user'
    assert result.status.value == 'completed'
    assert result.is_active is True
    assert result.model is None


def test_chat_message_public_assistant(
    assistant_message_data,
):
    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.role.value == 'assistant'
    assert result.status.value == 'completed'
    assert result.model == 'qwen2.5:7b'
    assert result.input_tokens == 100
    assert result.output_tokens == 50


@pytest.mark.parametrize(
    'status',
    ['pending', 'failed', 'cancelled', 'truncated'],
)
@pytest.mark.parametrize('content', ['', 'Resposta parcial'])
def test_chat_message_public_non_completed(
    assistant_message_data,
    status,
    content,
):
    assistant_message_data.update(
        status=status,
        content=content,
        is_active=False,
    )

    if status == 'pending':
        assistant_message_data['completed_at'] = None

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.status.value == status
    assert result.content == content
    assert result.is_active is False


def test_chat_message_public_inactive_completed(
    assistant_message_data,
):
    assistant_message_data['is_active'] = False

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.is_active is False
    assert result.status.value == 'completed'


def test_chat_message_public_regenerated(
    assistant_message_data,
):
    assistant_message_data.update(
        id=3,
        regenerated_from_id=2,
    )

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.regenerated_from_id == 2
    assert result.reply_to_message_id == 1


def test_chat_message_public_unknown_tokens(
    assistant_message_data,
):
    assistant_message_data.update(
        input_tokens=None,
        output_tokens=None,
    )

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.input_tokens is None
    assert result.output_tokens is None


def test_chat_message_public_zero_tokens(
    assistant_message_data,
):
    assistant_message_data.update(
        input_tokens=0,
        output_tokens=0,
    )

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.input_tokens == 0
    assert result.output_tokens == 0


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('id', 0),
        ('id', -1),
        ('id', True),
        ('id', '2'),
        ('conversation_id', 0),
        ('conversation_id', -1),
        ('conversation_id', True),
        ('conversation_id', '1'),
        ('input_tokens', -1),
        ('input_tokens', True),
        ('input_tokens', '100'),
        ('output_tokens', -1),
        ('output_tokens', True),
        ('output_tokens', '50'),
        ('reply_to_message_id', 0),
        ('reply_to_message_id', -1),
        ('reply_to_message_id', True),
        ('regenerated_from_id', 0),
        ('regenerated_from_id', -1),
        ('regenerated_from_id', True),
        ('role', 'system'),
        ('status', 'unknown'),
        ('content', None),
        ('content', 123),
        ('content', 'hello\x00world'),
        ('is_active', 1),
        ('is_active', 'true'),
        ('generation_id', 'invalid-uuid'),
        ('model', 'a' * 101),
    ],
)
def test_chat_message_public_invalid_fields(
    assistant_message_data,
    field,
    value,
):
    assistant_message_data[field] = value

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


@pytest.mark.parametrize(
    'status',
    ['pending', 'failed', 'cancelled', 'truncated'],
)
def test_chat_message_public_rejects_user_status(
    message_public_data,
    status,
):
    message_public_data['status'] = status

    if status == 'pending':
        message_public_data['completed_at'] = None

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(message_public_data)


@pytest.mark.parametrize('content', ['', ' ', '\t\n'])
def test_chat_message_public_rejects_empty_user(
    message_public_data,
    content,
):
    message_public_data['content'] = content

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(message_public_data)


def test_chat_message_public_rejects_inactive_user(
    message_public_data,
):
    message_public_data['is_active'] = False

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(message_public_data)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('model', 'qwen2.5:7b'),
        ('generation_id', '12345678-1234-5678-1234-567812345678'),
        ('input_tokens', 0),
        ('output_tokens', 0),
        ('reply_to_message_id', 2),
        ('regenerated_from_id', 2),
    ],
)
def test_chat_message_public_rejects_user_metadata(
    message_public_data,
    field,
    value,
):
    message_public_data[field] = value

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(message_public_data)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('model', None),
        ('model', ''),
        ('model', '   '),
        ('generation_id', None),
        ('reply_to_message_id', None),
    ],
)
def test_chat_message_public_requires_assistant_metadata(
    assistant_message_data,
    field,
    value,
):
    assistant_message_data[field] = value

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


@pytest.mark.parametrize('content', ['', ' ', '\t\n'])
def test_chat_message_public_rejects_empty_completed(
    assistant_message_data,
    content,
):
    assistant_message_data['content'] = content

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


@pytest.mark.parametrize(
    'status',
    ['pending', 'failed', 'cancelled', 'truncated'],
)
def test_chat_message_public_rejects_active_incomplete(
    assistant_message_data,
    status,
):
    assistant_message_data['status'] = status

    if status == 'pending':
        assistant_message_data['completed_at'] = None

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


def test_chat_message_public_pending_completion_time(
    assistant_message_data,
):
    assistant_message_data.update(
        status='pending',
        is_active=False,
    )

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


@pytest.mark.parametrize(
    'status',
    ['completed', 'failed', 'cancelled', 'truncated'],
)
def test_chat_message_public_requires_completion_time(
    assistant_message_data,
    status,
):
    assistant_message_data.update(
        status=status,
        completed_at=None,
        is_active=status == 'completed',
    )

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


@pytest.mark.parametrize(
    'field',
    ['created_at', 'completed_at'],
)
def test_chat_message_public_rejects_naive_datetime(
    assistant_message_data,
    field,
):
    assistant_message_data[field] = assistant_message_data[field].replace(
        tzinfo=None
    )

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


def test_chat_message_public_rejects_invalid_completion_order(
    assistant_message_data,
):

    assistant_message_data['completed_at'] = assistant_message_data[
        'created_at'
    ] - timedelta(seconds=1)

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


@pytest.mark.parametrize(
    'field',
    ['reply_to_message_id', 'regenerated_from_id'],
)
def test_chat_message_public_rejects_self_reference(
    assistant_message_data,
    field,
):
    assistant_message_data[field] = assistant_message_data['id']

    with pytest.raises(ValidationError):
        ChatMessagePublic.model_validate(assistant_message_data)


def test_chat_message_public_preserves_content(
    assistant_message_data,
):
    content = '  Exemplo:\n\n    return True\n  '

    assistant_message_data['content'] = content

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert result.content == content


def test_chat_message_public_accepts_long_response(
    assistant_message_data,
):
    assistant_message_data['content'] = 'a' * 10000

    result = ChatMessagePublic.model_validate(assistant_message_data)

    assert len(result.content) == 10000


def test_chat_message_public_excludes_internal_fields(
    assistant_message_data,
):
    assistant_message_data.update(
        user_id=1,
        system_prompt='Internal instructions',
        error_code='INTERNAL_ERROR',
    )

    result = ChatMessagePublic.model_validate(assistant_message_data)

    public_data = result.model_dump()

    assert 'user_id' not in public_data
    assert 'system_prompt' not in public_data
    assert 'error_code' not in public_data


def test_chat_message_public_from_orm(
    assistant_message_data,
):

    assistant_message_data.update(
        role=ChatMessageRole.ASSISTANT,
        status=ChatMessageStatus.COMPLETED,
    )

    message = ChatMessage(**assistant_message_data)

    result = ChatMessagePublic.model_validate(message)

    assert result.id == message.id
    assert result.content == message.content
    assert result.generation_id == message.generation_id


def test_chat_message_public_json_round_trip(
    assistant_message_data,
):
    original = ChatMessagePublic.model_validate(assistant_message_data)

    restored = ChatMessagePublic.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original


def test_chat_message_public_json_schema():
    schema = ChatMessagePublic.model_json_schema()

    expected = {
        'id',
        'conversation_id',
        'role',
        'content',
        'status',
        'model',
        'generation_id',
        'input_tokens',
        'output_tokens',
        'reply_to_message_id',
        'regenerated_from_id',
        'is_active',
        'created_at',
        'completed_at',
    }

    assert set(schema['properties']) == expected
    assert set(schema['required']) == expected


@pytest.fixture
def message_list_data(
    message_public_data,
    assistant_message_data,
):
    return {
        'items': [
            assistant_message_data,
            message_public_data,
        ],
        'total': 2,
        'page': 1,
        'page_size': 50,
        'pages': 1,
    }


def test_chat_message_list_valid(message_list_data):
    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.total == 2
    assert result.page == 1
    assert result.page_size == 50
    assert result.pages == 1
    assert len(result.items) == 2

    assert all(isinstance(item, ChatMessagePublic) for item in result.items)

    assert result.items[0].role.value == 'assistant'
    assert result.items[1].role.value == 'user'


def test_chat_message_list_empty(message_list_data):
    message_list_data.update(
        items=[],
        total=0,
        pages=0,
    )

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.items == []
    assert result.total == 0
    assert result.pages == 0


@pytest.mark.parametrize(
    ('total', 'page_size', 'pages'),
    [
        (2, 50, 1),
        (50, 50, 1),
        (51, 50, 2),
        (100, 50, 2),
        (101, 50, 3),
        (100, 100, 1),
        (101, 100, 2),
        (2, 2, 1),
    ],
)
def test_chat_message_list_page_calculation(
    message_list_data,
    total,
    page_size,
    pages,
):
    message_list_data.update(
        total=total,
        page_size=page_size,
        pages=pages,
    )

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.pages == pages


def test_chat_message_list_minimum_page_size(
    message_list_data,
):
    message_list_data.update(
        items=message_list_data['items'][:1],
        page_size=1,
        pages=2,
    )

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.page_size == 1
    assert len(result.items) == 1


def test_chat_message_list_last_page(message_list_data):
    message_list_data.update(
        total=102,
        page=3,
        pages=3,
    )

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.page == 3
    assert len(result.items) == 2


def test_chat_message_list_out_of_range(
    message_list_data,
):
    message_list_data.update(
        items=[],
        page=2,
    )

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.items == []
    assert result.page == 2


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('total', -1),
        ('total', True),
        ('total', '2'),
        ('page', 0),
        ('page', -1),
        ('page', True),
        ('page', '1'),
        ('page_size', 0),
        ('page_size', 101),
        ('page_size', True),
        ('page_size', '50'),
        ('pages', -1),
        ('pages', True),
        ('pages', '1'),
    ],
)
def test_chat_message_list_invalid_metadata(
    message_list_data,
    field,
    value,
):
    message_list_data[field] = value

    with pytest.raises(ValidationError):
        ChatMessageListResponse.model_validate(message_list_data)


@pytest.mark.parametrize('pages', [0, 2, 3])
def test_chat_message_list_wrong_pages(
    message_list_data,
    pages,
):
    message_list_data['pages'] = pages

    with pytest.raises(ValidationError) as exc:
        ChatMessageListResponse.model_validate(message_list_data)

    assert 'Invalid total number of pages' in str(exc.value)


def test_chat_message_list_rejects_page_overflow(
    message_list_data,
):
    message_list_data.update(
        page_size=1,
        pages=2,
    )

    with pytest.raises(ValidationError) as exc:
        ChatMessageListResponse.model_validate(message_list_data)

    assert 'Too many items' in str(exc.value)


def test_chat_message_list_rejects_last_page_overflow(
    message_list_data,
):
    message_list_data.update(
        total=51,
        page=2,
        pages=2,
    )

    with pytest.raises(ValidationError) as exc:
        ChatMessageListResponse.model_validate(message_list_data)

    assert 'Too many items' in str(exc.value)


def test_chat_message_list_rejects_out_of_range_items(
    message_list_data,
):
    message_list_data['page'] = 2

    with pytest.raises(ValidationError) as exc:
        ChatMessageListResponse.model_validate(message_list_data)

    assert 'Too many items' in str(exc.value)


def test_chat_message_list_rejects_invalid_item(
    message_list_data,
):
    message_list_data['items'][0]['id'] = 0

    with pytest.raises(ValidationError):
        ChatMessageListResponse.model_validate(message_list_data)


def test_chat_message_list_rejects_mixed_conversations(
    message_list_data,
):
    message_list_data['items'][0]['conversation_id'] = 2

    with pytest.raises(ValidationError) as exc:
        ChatMessageListResponse.model_validate(message_list_data)

    assert 'same conversation' in str(exc.value)


def test_chat_message_list_rejects_duplicate_ids(
    message_list_data,
):
    message_list_data['items'][1] = dict(message_list_data['items'][0])

    with pytest.raises(ValidationError) as exc:
        ChatMessageListResponse.model_validate(message_list_data)

    assert 'Message IDs must be unique' in str(exc.value)


@pytest.mark.parametrize(
    'status',
    ['pending', 'failed', 'cancelled', 'truncated'],
)
def test_chat_message_list_preserves_message_states(
    message_list_data,
    status,
):
    assistant = message_list_data['items'][0]

    assistant.update(
        status=status,
        is_active=False,
        content='Resposta parcial',
    )

    if status == 'pending':
        assistant['completed_at'] = None

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.items[0].status.value == status
    assert result.items[0].is_active is False
    assert result.items[0].content == 'Resposta parcial'


def test_chat_message_list_preserves_inactive_response(
    message_list_data,
):
    message_list_data['items'][0]['is_active'] = False

    result = ChatMessageListResponse.model_validate(message_list_data)

    assert result.items[0].status.value == 'completed'
    assert result.items[0].is_active is False


def test_chat_message_list_preserves_order(
    message_list_data,
):
    result = ChatMessageListResponse.model_validate(message_list_data)

    assert [item.id for item in result.items] == [2, 1]


@pytest.mark.parametrize(
    'field',
    ['items', 'total', 'page', 'page_size', 'pages'],
)
def test_chat_message_list_requires_fields(
    message_list_data,
    field,
):
    message_list_data.pop(field)

    with pytest.raises(ValidationError):
        ChatMessageListResponse.model_validate(message_list_data)


def test_chat_message_list_excludes_internal_fields(
    message_list_data,
):
    message_list_data['items'][0].update(
        user_id=1,
        system_prompt='Internal instructions',
        error_code='INTERNAL_ERROR',
    )

    result = ChatMessageListResponse.model_validate(message_list_data)

    payload = result.model_dump(mode='json')

    item = payload['items'][0]

    assert len(item) == 14
    assert 'user_id' not in item
    assert 'system_prompt' not in item
    assert 'error_code' not in item


def test_chat_message_list_from_orm(message_list_data):
    messages = [
        ChatMessage(**{
            **item,
            'role': ChatMessageRole(item['role']),
            'status': ChatMessageStatus(item['status']),
        })
        for item in message_list_data['items']
    ]

    result = ChatMessageListResponse.model_validate({
        **message_list_data,
        'items': messages,
    })

    assert len(result.items) == 2
    assert result.items[0].id == messages[0].id
    assert result.items[1].id == messages[1].id


def test_chat_message_list_json_round_trip(
    message_list_data,
):
    original = ChatMessageListResponse.model_validate(message_list_data)

    restored = ChatMessageListResponse.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original


def test_chat_message_list_json_schema():
    schema = ChatMessageListResponse.model_json_schema()

    expected = {
        'items',
        'total',
        'page',
        'page_size',
        'pages',
    }

    assert set(schema['properties']) == expected
    assert set(schema['required']) == expected

    properties = schema['properties']

    assert properties['total']['minimum'] == 0
    assert properties['page']['minimum'] == 1
    assert properties['page_size']['minimum'] == 1
    assert properties['page_size']['maximum'] == 100
    assert properties['pages']['minimum'] == 0

    assert properties['items']['type'] == 'array'
    assert properties['items']['items']['$ref'] == (
        '#/$defs/ChatMessagePublic'
    )


@pytest.fixture
def cancellation_response_data():
    return {
        'conversation_id': 1,
        'generation_id': uuid4(),
        'cancellation_requested': True,
    }


def test_chat_cancellation_response_valid(
    cancellation_response_data,
):
    result = ChatCancellationResponse.model_validate(
        cancellation_response_data
    )

    assert result.conversation_id == 1
    assert (
        result.generation_id == (cancellation_response_data['generation_id'])
    )
    assert result.cancellation_requested is True


def test_chat_cancellation_response_uuid_string(
    cancellation_response_data,
):
    generation_id = cancellation_response_data['generation_id']

    cancellation_response_data['generation_id'] = str(generation_id)

    result = ChatCancellationResponse.model_validate(
        cancellation_response_data
    )

    assert result.generation_id == generation_id


@pytest.mark.parametrize(
    'conversation_id',
    [0, -1, True, False, '1', 1.5, None],
)
def test_chat_cancellation_response_invalid_conversation_id(
    cancellation_response_data,
    conversation_id,
):
    cancellation_response_data['conversation_id'] = conversation_id

    with pytest.raises(ValidationError):
        ChatCancellationResponse.model_validate(cancellation_response_data)


@pytest.mark.parametrize(
    'generation_id',
    [
        None,
        '',
        'invalid-uuid',
        '12345678',
        123,
        True,
        [],
        {},
    ],
)
def test_chat_cancellation_response_invalid_generation_id(
    cancellation_response_data,
    generation_id,
):
    cancellation_response_data['generation_id'] = generation_id

    with pytest.raises(ValidationError):
        ChatCancellationResponse.model_validate(cancellation_response_data)


@pytest.mark.parametrize(
    'value',
    [
        False,
        None,
        0,
        1,
        1.0,
        'true',
        'false',
        '1',
        [],
        {},
    ],
)
def test_chat_cancellation_response_rejects_invalid_flag(
    cancellation_response_data,
    value,
):
    cancellation_response_data['cancellation_requested'] = value

    with pytest.raises(ValidationError) as exc:
        ChatCancellationResponse.model_validate(cancellation_response_data)

    assert any(
        error['loc'] == ('cancellation_requested',)
        for error in exc.value.errors()
    )


@pytest.mark.parametrize(
    'field',
    [
        'conversation_id',
        'generation_id',
        'cancellation_requested',
    ],
)
def test_chat_cancellation_response_requires_fields(
    cancellation_response_data,
    field,
):
    cancellation_response_data.pop(field)

    with pytest.raises(ValidationError) as exc:
        ChatCancellationResponse.model_validate(cancellation_response_data)

    assert any(
        error['type'] == 'missing' and error['loc'] == (field,)
        for error in exc.value.errors()
    )


def test_chat_cancellation_response_excludes_internal_fields(
    cancellation_response_data,
):
    cancellation_response_data.update(
        user_id=1,
        cancel_requested_at=None,
        generation_started_at=None,
        generation_expires_at=None,
        internal_error='Internal information',
        status='cancelled',
    )

    result = ChatCancellationResponse.model_validate(
        cancellation_response_data
    )

    assert set(result.model_dump()) == {
        'conversation_id',
        'generation_id',
        'cancellation_requested',
    }


def test_chat_cancellation_response_serialization(
    cancellation_response_data,
):
    result = ChatCancellationResponse.model_validate(
        cancellation_response_data
    )

    assert result.model_dump(mode='json') == {
        'conversation_id': 1,
        'generation_id': str(cancellation_response_data['generation_id']),
        'cancellation_requested': True,
    }


def test_chat_cancellation_response_json_round_trip(
    cancellation_response_data,
):
    original = ChatCancellationResponse.model_validate(
        cancellation_response_data
    )

    restored = ChatCancellationResponse.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original


def test_chat_cancellation_response_json_schema():
    schema = ChatCancellationResponse.model_json_schema()

    expected = {
        'conversation_id',
        'generation_id',
        'cancellation_requested',
    }

    assert set(schema['properties']) == expected
    assert set(schema['required']) == expected

    properties = schema['properties']

    assert properties['conversation_id']['type'] == ('integer')

    assert properties['conversation_id']['exclusiveMinimum'] == 0

    assert properties['generation_id']['format'] == 'uuid'

    assert properties['cancellation_requested']['const'] is True

    assert properties['cancellation_requested']['type'] == 'boolean'


@pytest.fixture
def chat_usage_data():
    return {
        'daily_limit': 50,
        'used': 18,
        'remaining': 32,
        'input_tokens': 12500,
        'output_tokens': 4800,
        'resets_at': datetime(2026, 11, 26, tzinfo=UTC),
    }


def test_chat_usage_response_valid(chat_usage_data):
    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert result.daily_limit == 50
    assert result.used == 18
    assert result.remaining == 32
    assert result.input_tokens == 12500
    assert result.output_tokens == 4800


def test_chat_usage_response_zero_usage(chat_usage_data):
    chat_usage_data.update(
        used=0,
        remaining=50,
        input_tokens=0,
        output_tokens=0,
    )

    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert result.used == 0
    assert result.remaining == 50
    assert result.input_tokens == 0
    assert result.output_tokens == 0


@pytest.mark.parametrize(
    ('daily_limit', 'used', 'remaining'),
    [
        (1, 0, 1),
        (1, 1, 0),
        (25, 10, 15),
        (50, 18, 32),
        (50, 49, 1),
        (50, 50, 0),
        (50, 51, 0),
        (25, 40, 0),
        (100, 50, 50),
        (1000, 200, 800),
    ],
)
def test_chat_usage_response_quota_calculation(
    chat_usage_data,
    daily_limit,
    used,
    remaining,
):
    chat_usage_data.update(
        daily_limit=daily_limit,
        used=used,
        remaining=remaining,
    )

    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert result.remaining == remaining


@pytest.mark.parametrize(
    'daily_limit',
    [0, -1, True, False, '50', 50.5, None],
)
def test_chat_usage_response_invalid_daily_limit(
    chat_usage_data,
    daily_limit,
):
    chat_usage_data['daily_limit'] = daily_limit

    with pytest.raises(ValidationError):
        ChatUsageResponse.model_validate(chat_usage_data)


@pytest.mark.parametrize(
    'field',
    [
        'used',
        'remaining',
        'input_tokens',
        'output_tokens',
    ],
)
@pytest.mark.parametrize(
    'value',
    [-1, True, False, '10', 1.5, None],
)
def test_chat_usage_response_invalid_counters(
    chat_usage_data,
    field,
    value,
):
    chat_usage_data[field] = value

    with pytest.raises(ValidationError):
        ChatUsageResponse.model_validate(chat_usage_data)


@pytest.mark.parametrize(
    ('daily_limit', 'used', 'remaining'),
    [
        (50, 18, 31),
        (50, 18, 33),
        (50, 18, 50),
        (50, 0, 0),
        (50, 50, 1),
        (25, 40, 1),
    ],
)
def test_chat_usage_response_inconsistent_quota(
    chat_usage_data,
    daily_limit,
    used,
    remaining,
):
    chat_usage_data.update(
        daily_limit=daily_limit,
        used=used,
        remaining=remaining,
    )

    with pytest.raises(ValidationError) as exc:
        ChatUsageResponse.model_validate(chat_usage_data)

    assert 'Invalid remaining daily quota' in str(exc.value)


@pytest.mark.parametrize(
    'resets_at',
    [
        '2026-11-26T00:00:00Z',
        '2026-11-26T00:00:00+00:00',
        '2026-12-01T00:00:00Z',
        '2027-01-01T00:00:00Z',
    ],
)
def test_chat_usage_response_valid_reset_time(
    chat_usage_data,
    resets_at,
):
    chat_usage_data['resets_at'] = resets_at

    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert result.resets_at.utcoffset() == timedelta(0)
    assert result.resets_at.hour == 0
    assert result.resets_at.minute == 0


@pytest.mark.parametrize(
    'resets_at',
    [
        None,
        '',
        'invalid-date',
        '2026-11-26T00:00:00',
        datetime(2026, 11, 26),
        '2026-11-26T00:00:00-03:00',
        '2026-11-26T00:00:00+01:00',
        '2026-11-26T01:00:00Z',
        '2026-11-26T00:01:00Z',
        '2026-11-26T00:00:01Z',
        '2026-11-26T00:00:00.000001Z',
    ],
)
def test_chat_usage_response_invalid_reset_time(
    chat_usage_data,
    resets_at,
):
    chat_usage_data['resets_at'] = resets_at

    with pytest.raises(ValidationError):
        ChatUsageResponse.model_validate(chat_usage_data)


def test_chat_usage_response_large_token_counters(
    chat_usage_data,
):
    chat_usage_data.update(
        input_tokens=10_000_000_000,
        output_tokens=5_000_000_000,
    )

    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert result.input_tokens == 10_000_000_000
    assert result.output_tokens == 5_000_000_000


@pytest.mark.parametrize(
    'field',
    [
        'daily_limit',
        'used',
        'remaining',
        'input_tokens',
        'output_tokens',
        'resets_at',
    ],
)
def test_chat_usage_response_requires_fields(
    chat_usage_data,
    field,
):
    chat_usage_data.pop(field)

    with pytest.raises(ValidationError) as exc:
        ChatUsageResponse.model_validate(chat_usage_data)

    assert any(
        error['type'] == 'missing' and error['loc'] == (field,)
        for error in exc.value.errors()
    )


def test_chat_usage_response_excludes_internal_fields(
    chat_usage_data,
):
    chat_usage_data.update(
        id=1,
        user_id=2,
        usage_date='2026-11-25',
        request_count=18,
        created_at=None,
        updated_at=None,
        internal_error='Internal information',
    )

    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert set(result.model_dump()) == {
        'daily_limit',
        'used',
        'remaining',
        'input_tokens',
        'output_tokens',
        'resets_at',
    }


def test_chat_usage_response_serialization(
    chat_usage_data,
):
    result = ChatUsageResponse.model_validate(chat_usage_data)

    assert result.model_dump(mode='json') == {
        'daily_limit': 50,
        'used': 18,
        'remaining': 32,
        'input_tokens': 12500,
        'output_tokens': 4800,
        'resets_at': '2026-11-26T00:00:00Z',
    }


def test_chat_usage_response_json_round_trip(
    chat_usage_data,
):
    original = ChatUsageResponse.model_validate(chat_usage_data)

    restored = ChatUsageResponse.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original


def test_chat_usage_response_json_schema():
    schema = ChatUsageResponse.model_json_schema()

    expected = {
        'daily_limit',
        'used',
        'remaining',
        'input_tokens',
        'output_tokens',
        'resets_at',
    }

    assert set(schema['properties']) == expected
    assert set(schema['required']) == expected

    properties = schema['properties']

    assert properties['daily_limit']['exclusiveMinimum'] == 0

    for field in (
        'used',
        'remaining',
        'input_tokens',
        'output_tokens',
    ):
        assert properties[field]['minimum'] == 0
        assert properties[field]['type'] == 'integer'

    assert properties['resets_at']['format'] == ('date-time')


@pytest.fixture
def stream_event_adapter():
    return TypeAdapter(ChatStreamEvent)


@pytest.fixture
def stream_event_data(assistant_message_data):
    return {
        'conversation_id': (assistant_message_data['conversation_id']),
        'generation_id': (assistant_message_data['generation_id']),
        'assistant_message_id': (assistant_message_data['id']),
    }


@pytest.fixture
def stream_terminal_data(
    stream_event_data,
    assistant_message_data,
):
    return {
        **stream_event_data,
        'type': 'response.completed',
        'message': assistant_message_data,
    }


def test_chat_stream_event_message_created(
    stream_event_adapter,
    stream_event_data,
):
    result = stream_event_adapter.validate_python({
        **stream_event_data,
        'type': 'message.created',
        'user_message_id': 1,
    })

    assert result.type == 'message.created'
    assert result.user_message_id == 1
    assert result.assistant_message_id == 2
    assert result.regenerated_from_id is None


def test_chat_stream_event_regeneration(
    stream_event_adapter,
    stream_event_data,
):
    result = stream_event_adapter.validate_python({
        **stream_event_data,
        'type': 'message.created',
        'user_message_id': 1,
        'regenerated_from_id': 3,
    })

    assert result.regenerated_from_id == 3


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('user_message_id', 0),
        ('user_message_id', -1),
        ('user_message_id', True),
        ('user_message_id', '1'),
        ('user_message_id', 2),
        ('regenerated_from_id', 0),
        ('regenerated_from_id', -1),
        ('regenerated_from_id', True),
        ('regenerated_from_id', 1),
        ('regenerated_from_id', 2),
    ],
)
def test_chat_stream_event_invalid_created(
    stream_event_adapter,
    stream_event_data,
    field,
    value,
):
    payload = {
        **stream_event_data,
        'type': 'message.created',
        'user_message_id': 1,
        field: value,
    }

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(payload)


@pytest.mark.parametrize(
    'delta',
    [
        'Olá',
        ' ',
        '\n',
        '\t',
        '    return True',
        '```python\n',
        'a' * 10000,
    ],
)
def test_chat_stream_event_preserves_delta(
    stream_event_adapter,
    stream_event_data,
    delta,
):
    result = stream_event_adapter.validate_python({
        **stream_event_data,
        'type': 'response.delta',
        'delta': delta,
    })

    assert result.delta == delta


@pytest.mark.parametrize(
    'delta',
    ['', None, 123, True, [], {}, 'a\x00b'],
)
def test_chat_stream_event_invalid_delta(
    stream_event_adapter,
    stream_event_data,
    delta,
):
    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python({
            **stream_event_data,
            'type': 'response.delta',
            'delta': delta,
        })


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('conversation_id', 0),
        ('conversation_id', -1),
        ('conversation_id', True),
        ('conversation_id', '1'),
        ('assistant_message_id', 0),
        ('assistant_message_id', -1),
        ('assistant_message_id', True),
        ('assistant_message_id', '2'),
        ('generation_id', None),
        ('generation_id', 'invalid-uuid'),
        ('generation_id', 123),
    ],
)
def test_chat_stream_event_invalid_common_fields(
    stream_event_adapter,
    stream_event_data,
    field,
    value,
):
    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python({
            **stream_event_data,
            'type': 'response.delta',
            'delta': 'Olá',
            field: value,
        })


@pytest.mark.parametrize(
    'field',
    [
        'type',
        'conversation_id',
        'generation_id',
        'assistant_message_id',
        'delta',
    ],
)
def test_chat_stream_event_required_fields(
    stream_event_adapter,
    stream_event_data,
    field,
):
    payload = {
        **stream_event_data,
        'type': 'response.delta',
        'delta': 'Olá',
    }

    payload.pop(field)

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(payload)


@pytest.mark.parametrize(
    'event_type',
    [
        '',
        'unknown',
        'response.pending',
        'response.error',
        None,
    ],
)
def test_chat_stream_event_invalid_type(
    stream_event_adapter,
    stream_event_data,
    event_type,
):
    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python({
            **stream_event_data,
            'type': event_type,
            'delta': 'Olá',
        })


@pytest.mark.parametrize(
    'field',
    [
        'user_id',
        'system_prompt',
        'api_key',
        'internal_error',
        'unexpected_field',
    ],
)
def test_chat_stream_event_rejects_extra_fields(
    stream_event_adapter,
    stream_event_data,
    field,
):
    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python({
            **stream_event_data,
            'type': 'response.delta',
            'delta': 'Olá',
            field: 'unexpected',
        })


@pytest.mark.parametrize(
    'status',
    ['completed', 'cancelled', 'failed', 'truncated'],
)
def test_chat_stream_event_terminal_states(
    stream_event_adapter,
    stream_terminal_data,
    status,
):
    stream_terminal_data['type'] = f'response.{status}'

    stream_terminal_data['message'].update(
        status=status,
        is_active=status == 'completed',
    )

    if status == 'failed':
        stream_terminal_data['error_code'] = 'PROVIDER_UNAVAILABLE'

    result = stream_event_adapter.validate_python(stream_terminal_data)

    assert result.type == f'response.{status}'
    assert result.message.status.value == status
    assert result.message.is_active == (status == 'completed')


@pytest.mark.parametrize(
    ('event_type', 'status'),
    [
        ('response.completed', 'cancelled'),
        ('response.cancelled', 'completed'),
        ('response.failed', 'truncated'),
        ('response.truncated', 'failed'),
    ],
)
def test_chat_stream_event_rejects_wrong_status(
    stream_event_adapter,
    stream_terminal_data,
    event_type,
    status,
):
    stream_terminal_data['type'] = event_type

    stream_terminal_data['message'].update(
        status=status,
        is_active=status == 'completed',
    )

    if event_type == 'response.failed':
        stream_terminal_data['error_code'] = 'PROVIDER_UNAVAILABLE'

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


@pytest.mark.parametrize(
    'field',
    [
        'conversation_id',
        'assistant_message_id',
        'generation_id',
    ],
)
def test_chat_stream_event_identity_mismatch(
    stream_event_adapter,
    stream_terminal_data,
    field,
):
    stream_terminal_data[field] = uuid4() if field == 'generation_id' else 99

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


def test_chat_stream_event_rejects_user_message(
    stream_event_adapter,
    stream_terminal_data,
    message_public_data,
):
    stream_terminal_data['message'] = message_public_data
    stream_terminal_data['assistant_message_id'] = 1

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


def test_chat_stream_event_rejects_inactive_completion(
    stream_event_adapter,
    stream_terminal_data,
):
    stream_terminal_data['message']['is_active'] = False

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


@pytest.mark.parametrize(
    'error_code',
    [
        'MODEL_NOT_FOUND',
        'PROVIDER_REQUEST_ERROR',
        'PROVIDER_UNAVAILABLE',
        'GENERATION_TIMEOUT',
        'INVALID_PROVIDER_RESPONSE',
        'STREAM_INTERRUPTED',
        'INTERNAL_ERROR',
    ],
)
def test_chat_stream_event_valid_error_codes(
    stream_event_adapter,
    stream_terminal_data,
    error_code,
):
    stream_terminal_data.update(
        type='response.failed',
        error_code=error_code,
    )

    stream_terminal_data['message'].update(
        status='failed',
        is_active=False,
    )

    result = stream_event_adapter.validate_python(stream_terminal_data)

    assert result.error_code.value == error_code


@pytest.mark.parametrize(
    'error_code',
    ['', None, 'UNKNOWN_ERROR', 'Raw exception details'],
)
def test_chat_stream_event_invalid_error_codes(
    stream_event_adapter,
    stream_terminal_data,
    error_code,
):
    stream_terminal_data.update(
        type='response.failed',
        error_code=error_code,
    )

    stream_terminal_data['message'].update(
        status='failed',
        is_active=False,
    )

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


def test_chat_stream_event_requires_error_code(
    stream_event_adapter,
    stream_terminal_data,
):
    stream_terminal_data['type'] = 'response.failed'

    stream_terminal_data['message'].update(
        status='failed',
        is_active=False,
    )

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


def test_chat_stream_event_requires_terminal_message(
    stream_event_adapter,
    stream_terminal_data,
):
    stream_terminal_data.pop('message')

    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python(stream_terminal_data)


def test_chat_stream_event_requires_user_message_id(
    stream_event_adapter,
    stream_event_data,
):
    with pytest.raises(ValidationError):
        stream_event_adapter.validate_python({
            **stream_event_data,
            'type': 'message.created',
        })


def test_chat_stream_event_json_round_trip(
    stream_event_adapter,
    stream_terminal_data,
):
    original = stream_event_adapter.validate_python(stream_terminal_data)

    restored = stream_event_adapter.validate_json(
        stream_event_adapter.dump_json(original)
    )

    assert restored == original


def test_chat_stream_event_json_schema(
    stream_event_adapter,
):
    schema = stream_event_adapter.json_schema()

    assert schema['discriminator']['propertyName'] == 'type'

    assert set(schema['discriminator']['mapping']) == {
        'message.created',
        'response.delta',
        'response.completed',
        'response.cancelled',
        'response.failed',
        'response.truncated',
        'response.error',
    }

    assert len(schema['oneOf']) == len(schema['discriminator']['mapping'])


@pytest.mark.parametrize(
    'schema',
    [
        ChatConversationCreate,
        ChatConversationUpdate,
        ChatConversationPublic,
    ],
)
@pytest.mark.parametrize(
    'title',
    [
        '\x00',
        '\x00Suporte',
        'Suporte\x00',
        'Suporte\x00tecnico',
        ' \x00 ',
    ],
)
def test_chat_consolidated_rejects_null_title(
    schema,
    title,
    conversation_public_data,
):
    if schema is ChatConversationPublic:
        payload = {
            **conversation_public_data,
            'title': title,
        }
    else:
        payload = {'title': title}

    with pytest.raises(ValidationError) as exc:
        schema.model_validate(payload)

    assert 'cannot contain null characters' in str(exc.value)


def test_chat_consolidated_preserves_optional_title():
    result = ChatConversationCreate(title=None)

    assert result.title is None


@pytest.mark.parametrize(
    'title',
    [
        'Suporte técnico',
        'Configuração do PostgreSQL',
        'Problema com conexão',
        'Servidor — ambiente de desenvolvimento',
        '  Suporte técnico  ',
    ],
)
def test_chat_consolidated_preserves_valid_title(title):
    created = ChatConversationCreate(title=title)
    updated = ChatConversationUpdate(title=title)

    assert created.title == title.strip()
    assert updated.title == title.strip()


@pytest.mark.parametrize(
    'offset',
    [
        timedelta(0),
        timedelta(seconds=1),
        timedelta(minutes=10),
        timedelta(days=1),
    ],
)
def test_chat_consolidated_valid_conversation_timestamps(
    conversation_public_data,
    offset,
):
    created_at = conversation_public_data['created_at']

    conversation_public_data['updated_at'] = created_at + offset

    result = ChatConversationPublic.model_validate(conversation_public_data)

    assert result.updated_at >= result.created_at


@pytest.mark.parametrize(
    'offset',
    [
        timedelta(microseconds=1),
        timedelta(seconds=1),
        timedelta(days=1),
    ],
)
def test_chat_consolidated_invalid_conversation_timestamps(
    conversation_public_data,
    offset,
):
    conversation_public_data['updated_at'] = (
        conversation_public_data['created_at'] - offset
    )

    with pytest.raises(ValidationError) as exc:
        ChatConversationPublic.model_validate(conversation_public_data)

    assert 'Updated at cannot precede created at' in str(exc.value)


def test_chat_cancellation_request_valid_uuid():
    generation_id = uuid4()

    result = ChatCancellationRequest(generation_id=generation_id)

    assert result.generation_id == generation_id


def test_chat_cancellation_request_valid_uuid_string():
    generation_id = uuid4()

    result = ChatCancellationRequest.model_validate({
        'generation_id': str(generation_id),
    })

    assert result.generation_id == generation_id


@pytest.mark.parametrize(
    'generation_id',
    [
        None,
        '',
        'invalid-uuid',
        '550e8400-e29b-41d4-a716',
        123,
        True,
        [],
        {},
    ],
)
def test_chat_cancellation_request_invalid_uuid(
    generation_id,
):
    with pytest.raises(ValidationError):
        ChatCancellationRequest.model_validate({
            'generation_id': generation_id,
        })


def test_chat_cancellation_request_requires_generation_id():
    with pytest.raises(ValidationError):
        ChatCancellationRequest.model_validate({})


@pytest.mark.parametrize(
    'field',
    [
        'user_id',
        'conversation_id',
        'assistant_message_id',
        'status',
        'cancellation_requested',
        'unexpected_field',
    ],
)
def test_chat_cancellation_request_rejects_extra_fields(
    field,
):
    with pytest.raises(ValidationError):
        ChatCancellationRequest.model_validate({
            'generation_id': uuid4(),
            field: 'unexpected',
        })


def test_chat_cancellation_request_json_round_trip():
    original = ChatCancellationRequest(generation_id=uuid4())

    restored = ChatCancellationRequest.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original


def test_chat_cancellation_request_json_schema():
    schema = ChatCancellationRequest.model_json_schema()

    assert set(schema['properties']) == {
        'generation_id',
    }

    assert schema['required'] == ['generation_id']

    assert schema['additionalProperties'] is False

    assert schema['properties']['generation_id']['format'] == 'uuid'


def test_chat_consolidated_generation_contract(
    conversation_public_data,
    message_public_data,
    assistant_message_data,
):
    generation_id = assistant_message_data['generation_id']

    conversation_public_data.update(
        id=assistant_message_data['conversation_id'],
        generation_status='generating',
        generation_id=generation_id,
    )

    conversation = ChatConversationPublic.model_validate(
        conversation_public_data
    )

    request = ChatMessageCreate(content=message_public_data['content'])

    user_message = ChatMessagePublic.model_validate(message_public_data)

    assistant_message = ChatMessagePublic.model_validate(
        assistant_message_data
    )

    adapter = TypeAdapter(ChatStreamEvent)

    common = {
        'conversation_id': conversation.id,
        'generation_id': generation_id,
        'assistant_message_id': assistant_message.id,
    }

    created = adapter.validate_python({
        **common,
        'type': 'message.created',
        'user_message_id': user_message.id,
    })

    completed = adapter.validate_python({
        **common,
        'type': 'response.completed',
        'message': assistant_message,
    })

    history = ChatMessageListResponse(
        items=[assistant_message, user_message],
        total=2,
        page=1,
        page_size=50,
        pages=1,
    )

    assert request.content == user_message.content
    assert created.generation_id == conversation.generation_id
    assert created.user_message_id == user_message.id

    assert assistant_message.reply_to_message_id == (user_message.id)

    assert completed.message == history.items[0]
    assert history.items[1] == user_message

    restored = ChatMessageListResponse.model_validate_json(
        history.model_dump_json()
    )

    assert restored == history


def test_chat_consolidated_cancellation_contract(
    conversation_public_data,
    assistant_message_data,
):
    generation_id = assistant_message_data['generation_id']

    conversation_public_data.update(
        id=assistant_message_data['conversation_id'],
        generation_status='generating',
        generation_id=generation_id,
    )

    conversation = ChatConversationPublic.model_validate(
        conversation_public_data
    )

    request = ChatCancellationRequest(generation_id=generation_id)

    response = ChatCancellationResponse(
        conversation_id=conversation.id,
        generation_id=request.generation_id,
        cancellation_requested=True,
    )

    assistant_message_data.update(
        status='cancelled',
        is_active=False,
    )

    adapter = TypeAdapter(ChatStreamEvent)

    event = adapter.validate_python({
        'type': 'response.cancelled',
        'conversation_id': response.conversation_id,
        'generation_id': response.generation_id,
        'assistant_message_id': assistant_message_data['id'],
        'message': assistant_message_data,
    })

    assert conversation.generation_id == request.generation_id
    assert response.generation_id == event.generation_id
    assert response.cancellation_requested is True
    assert event.message.status == ChatMessageStatus.CANCELLED
    assert event.message.is_active is False


def test_chat_consolidated_stream_content_preservation(
    stream_event_data,
    assistant_message_data,
):
    adapter = TypeAdapter(ChatStreamEvent)

    chunks = [
        'Verifique o serviço:\n\n',
        '```bash\n',
        'systemctl status postgresql\n',
        '```\n',
    ]

    received = []

    for chunk in chunks:
        event = adapter.validate_python({
            **stream_event_data,
            'type': 'response.delta',
            'delta': chunk,
        })

        restored = adapter.validate_json(adapter.dump_json(event))

        received.append(restored.delta)

    assistant_message_data['content'] = ''.join(chunks)

    completed = adapter.validate_python({
        **stream_event_data,
        'type': 'response.completed',
        'message': assistant_message_data,
    })

    assert ''.join(received) == completed.message.content
    assert completed.message.content == ''.join(chunks)
