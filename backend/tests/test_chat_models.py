import pytest
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import (
    Base,
    ChatConversation,
    ChatGenerationAttempt,
    ChatMessage,
    ChatUsage,
    User,
)
from app.models.chat_conversation import ChatGenerationStatus
from app.models.chat_generation_attempt import (
    ChatGenerationAttemptStatus,
)
from app.models.chat_message import (
    ChatMessageRole,
    ChatMessageStatus,
)

CHAT_MODELS = (
    ChatConversation,
    ChatMessage,
    ChatUsage,
    ChatGenerationAttempt,
)


# 1. Table registration and structure: 5 tests.


def test_chat_tables_registered():
    configure_mappers()

    assert set(Base.metadata.tables) == {
        'users',
        'tickets',
        'ai_analyses',
        'chat_conversations',
        'chat_messages',
        'chat_usage',
        'chat_generation_attempts',
    }


@pytest.mark.parametrize(
    ('model', 'table_name', 'column_count'),
    [
        (ChatConversation, 'chat_conversations', 10),
        (ChatMessage, 'chat_messages', 14),
        (ChatUsage, 'chat_usage', 8),
        (
            ChatGenerationAttempt,
            'chat_generation_attempts',
            11,
        ),
    ],
)
def test_chat_table_structure(
    model,
    table_name,
    column_count,
):
    table = model.__table__

    assert table.name == table_name
    assert len(table.columns) == column_count
    assert table is Base.metadata.tables[table_name]


# 2. Enum values: 4 tests.


@pytest.mark.parametrize(
    ('enum_class', 'expected'),
    [
        (
            ChatGenerationStatus,
            {'idle', 'generating'},
        ),
        (
            ChatMessageRole,
            {'user', 'assistant'},
        ),
        (
            ChatMessageStatus,
            {
                'pending',
                'completed',
                'failed',
                'cancelled',
                'truncated',
            },
        ),
        (
            ChatGenerationAttemptStatus,
            {
                'running',
                'completed',
                'failed',
                'cancelled',
                'truncated',
                'expired',
            },
        ),
    ],
)
def test_chat_enum_values(enum_class, expected):
    assert {item.value for item in enum_class} == expected


# 3. Relationships: 4 tests.


@pytest.mark.parametrize(
    ('source', 'name', 'target', 'reverse'),
    [
        (
            User,
            'chat_conversations',
            ChatConversation,
            'user',
        ),
        (
            User,
            'chat_usage',
            ChatUsage,
            'user',
        ),
        (
            User,
            'chat_generation_attempts',
            ChatGenerationAttempt,
            'user',
        ),
        (
            ChatConversation,
            'messages',
            ChatMessage,
            'conversation',
        ),
    ],
)
def test_chat_relationships(
    source,
    name,
    target,
    reverse,
):
    configure_mappers()

    relation = source.__mapper__.relationships[name]
    reverse_relation = target.__mapper__.relationships[reverse]

    assert relation.mapper.class_ is target
    assert relation.back_populates == reverse
    assert relation.uselist
    assert relation.passive_deletes
    assert 'delete-orphan' in relation.cascade

    assert reverse_relation.mapper.class_ is source
    assert reverse_relation.back_populates == name
    assert not reverse_relation.uselist


# 4. Foreign keys: 4 tests.


@pytest.mark.parametrize(
    ('model', 'column_name', 'target'),
    [
        (
            ChatConversation,
            'user_id',
            'users.id',
        ),
        (
            ChatUsage,
            'user_id',
            'users.id',
        ),
        (
            ChatGenerationAttempt,
            'user_id',
            'users.id',
        ),
    ],
)
def test_chat_user_foreign_keys(
    model,
    column_name,
    target,
):
    table = model.__table__
    column = table.c[column_name]

    assert not column.nullable
    assert len(table.foreign_keys) == 1

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == target
    assert foreign_key.ondelete == 'CASCADE'


def test_message_foreign_keys():
    table = ChatMessage.__table__

    conversation_fk = next(iter(table.c.conversation_id.foreign_keys))

    assert not table.c.conversation_id.nullable

    constraints = [
        item
        for item in table.constraints
        if isinstance(item, ForeignKeyConstraint)
    ]

    assert len(constraints) == 3

    direct_fk = next(
        item
        for item in constraints
        if list(item.columns.keys()) == ['conversation_id']
    )

    assert direct_fk.elements[0].target_fullname == ('chat_conversations.id')
    assert direct_fk.ondelete == 'CASCADE'
    assert conversation_fk is not None

    expected = {
        'fk_chat_messages_reply_same_conversation': 'reply_to_message_id',
        'fk_chat_messages_regen_same_conversation': 'regenerated_from_id',
    }

    for name, reference in expected.items():
        constraint = next(item for item in constraints if item.name == name)

        assert list(constraint.columns.keys()) == [
            'conversation_id',
            reference,
        ]

        assert [item.target_fullname for item in constraint.elements] == [
            'chat_messages.conversation_id',
            'chat_messages.id',
        ]

        assert constraint.ondelete == 'CASCADE'


# 5. Check constraints: 4 tests.


@pytest.mark.parametrize(
    ('model', 'expected'),
    [
        (
            ChatConversation,
            {
                'ck_chat_conversations_title_not_empty',
                'ck_chat_conversations_generation_state',
                'ck_chat_conversations_cancel_time',
            },
        ),
        (
            ChatMessage,
            {
                'ck_chat_messages_input_tokens',
                'ck_chat_messages_output_tokens',
                'ck_chat_messages_role_fields',
                'ck_chat_messages_completion_state',
                'ck_chat_messages_completed_content',
                'ck_chat_messages_active_state',
                'ck_chat_messages_reply_not_self',
                'ck_chat_messages_regeneration_not_self',
                'ck_chat_messages_model_not_empty',
                'ck_chat_messages_completed_at',
            },
        ),
        (
            ChatUsage,
            {
                'ck_chat_usage_request_count',
                'ck_chat_usage_input_tokens',
                'ck_chat_usage_output_tokens',
            },
        ),
        (
            ChatGenerationAttempt,
            {
                'ck_chat_attempts_expiration',
                'ck_chat_attempts_completion_state',
                'ck_chat_attempts_finished_at',
                'ck_chat_attempts_input_tokens',
                'ck_chat_attempts_output_tokens',
                'ck_chat_attempts_model_not_empty',
                'ck_chat_attempts_error_state',
            },
        ),
    ],
)
def test_chat_check_constraints(model, expected):
    constraints = {
        item.name
        for item in model.__table__.constraints
        if isinstance(item, CheckConstraint)
    }

    assert constraints == expected


# 6. Unique constraints: 3 tests.


@pytest.mark.parametrize(
    ('model', 'columns'),
    [
        (ChatUsage, ['user_id', 'usage_date']),
        (ChatMessage, ['conversation_id', 'id']),
    ],
)
def test_chat_composite_unique_constraints(
    model,
    columns,
):
    constraints = [
        list(item.columns.keys())
        for item in model.__table__.constraints
        if isinstance(item, UniqueConstraint)
    ]

    assert columns in constraints


def test_generation_id_uniqueness():
    assert ChatConversation.__table__.c.generation_id.unique
    assert ChatMessage.__table__.c.generation_id.unique

    assert ChatGenerationAttempt.__table__.c.generation_id.primary_key


# 7. Indexes: 4 tests.


def test_conversation_listing_index():
    indexes = {item.name: item for item in ChatConversation.__table__.indexes}

    index = indexes['ix_chat_conversations_user_updated']

    assert list(index.columns.keys()) == [
        'user_id',
        'updated_at',
        'id',
    ]


def test_message_active_reply_index():
    index = next(
        item
        for item in ChatMessage.__table__.indexes
        if item.name == 'uq_chat_messages_active_reply'
    )

    assert index.unique

    assert list(index.columns.keys()) == [
        'reply_to_message_id',
    ]

    predicate = str(index.dialect_options['postgresql']['where'])

    assert "role = 'assistant'" in predicate
    assert "status = 'completed'" in predicate
    assert 'is_active = true' in predicate


def test_generation_rate_limit_index():
    index = next(
        item
        for item in ChatGenerationAttempt.__table__.indexes
        if item.name == 'ix_chat_attempts_user_reserved'
    )

    assert list(index.columns.keys()) == [
        'user_id',
        'reserved_at',
    ]


def test_generation_running_indexes():
    indexes = {
        item.name: item for item in ChatGenerationAttempt.__table__.indexes
    }

    expected = {
        'ix_chat_attempts_running_expiration': 'expires_at',
        'ix_chat_attempts_running_user': 'user_id',
    }

    for name, column in expected.items():
        index = indexes[name]

        assert list(index.columns.keys()) == [column]

        predicate = str(index.dialect_options['postgresql']['where'])

        assert predicate == "status = 'running'"


# 8. Default values: 3 tests.


def test_conversation_defaults():
    columns = ChatConversation.__table__.c

    assert columns.title.default.arg == 'Nova conversa'
    assert columns.title.server_default.arg == ('Nova conversa')

    assert columns.generation_status.default.arg == (ChatGenerationStatus.IDLE)

    assert columns.generation_status.server_default.arg == 'idle'


def test_usage_counter_defaults():
    columns = ChatUsage.__table__.c

    for name in (
        'request_count',
        'input_tokens',
        'output_tokens',
    ):
        assert columns[name].default.arg == 0
        assert columns[name].server_default.arg == '0'
        assert not columns[name].nullable


def test_generation_attempt_defaults():
    column = ChatGenerationAttempt.__table__.c.status

    assert column.default.arg == (ChatGenerationAttemptStatus.RUNNING)

    assert column.server_default.arg == 'running'


# 9. Data types: 3 tests.


def test_generation_uuid_types():
    for model in (
        ChatConversation,
        ChatMessage,
        ChatGenerationAttempt,
    ):
        column = model.__table__.c.generation_id

        assert isinstance(column.type, Uuid)
        assert column.type.as_uuid


def test_usage_date_and_counter_types():
    for model in (ChatUsage, ChatGenerationAttempt):
        assert isinstance(
            model.__table__.c.usage_date.type,
            Date,
        )

    for name in (
        'request_count',
        'input_tokens',
        'output_tokens',
    ):
        assert isinstance(
            ChatUsage.__table__.c[name].type,
            BigInteger,
        )


def test_chat_datetime_timezone_types():
    for model in CHAT_MODELS:
        for column in model.__table__.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone, column.name


# 10. PostgreSQL DDL compilation: 4 tests.


@pytest.mark.parametrize('model', CHAT_MODELS)
def test_chat_postgresql_ddl_compilation(model):
    table = model.__table__
    dialect = postgresql.dialect()

    ddl = str(CreateTable(table).compile(dialect=dialect))

    assert f'CREATE TABLE {table.name}' in ddl
    assert 'PRIMARY KEY' in ddl
    assert 'TIMESTAMP WITH TIME ZONE' in ddl
    assert 'ON DELETE CASCADE' in ddl

    for constraint in table.constraints:
        if isinstance(constraint, CheckConstraint):
            assert constraint.name in ddl

    for index in table.indexes:
        index_ddl = str(CreateIndex(index).compile(dialect=dialect))

        assert index.name in index_ddl
        assert table.name in index_ddl
