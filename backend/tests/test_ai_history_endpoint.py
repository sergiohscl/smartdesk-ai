from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.ai_analysis import AIAnalysis
from app.models.ticket import TicketPriority
from app.models.user import User, UserRole


def make_user(
    user_id: int = 1,
    role: UserRole = UserRole.USER,
    active: bool = True,
) -> User:
    return User(
        id=user_id,
        name='Usuário Teste',
        email=f'user{user_id}@teste.com',
        hashed_password='hashed-password',
        is_active=active,
        role=role,
        created_at=datetime.now(UTC),
    )


def make_analysis(
    analysis_id: int,
    ticket_id: int = 10,
    analyzed_by_id: int = 1,
    created_at: datetime | None = None,
) -> AIAnalysis:
    return AIAnalysis(
        id=analysis_id,
        ticket_id=ticket_id,
        suggested_priority=TicketPriority.HIGH,
        suggested_category='hardware',
        reason='Possível falha física no computador.',
        priority_at_analysis=TicketPriority.MEDIUM,
        analyzed_by_id=analyzed_by_id,
        created_at=created_at or datetime.now(UTC),
        applied_at=None,
        applied_by_id=None,
    )


def configure_history_session(
    mock_session,
    user: User,
    ticket_id: int | None,
    analyses: list[AIAnalysis] | None = None,
):
    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    ticket_result = MagicMock()
    ticket_result.scalar_one_or_none.return_value = ticket_id

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = analyses or []

    mock_session.execute.side_effect = [
        auth_result,
        ticket_result,
        history_result,
    ]

    mock_session.scalar.return_value = len(analyses or [])


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {'Authorization': f'Bearer {token}'}


@pytest.mark.asyncio
async def test_get_ai_history_success(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    now = datetime.now(UTC)

    analyses = [
        make_analysis(3, created_at=now),
        make_analysis(2, created_at=now - timedelta(minutes=1)),
        make_analysis(1, created_at=now - timedelta(minutes=2)),
    ]

    configure_history_session(mock_session, user, 10, analyses)

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 3
    assert data['page'] == 1
    assert data['page_size'] == 10
    assert data['pages'] == 1
    assert len(data['items']) == 3

    assert [item['id'] for item in data['items']] == [3, 2, 1]

    first = data['items'][0]

    assert first['ticket_id'] == 10
    assert first['suggested_priority'] == 'high'
    assert first['suggested_category'] == 'hardware'
    assert first['priority_at_analysis'] == 'medium'
    assert first['analyzed_by_id'] == user.id
    assert first['applied_at'] is None
    assert first['applied_by_id'] is None

    mock_session.commit.assert_not_awaited()
    mock_session.add.assert_not_called()
    mock_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_ai_history_empty(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    configure_history_session(mock_session, user, 10, [])

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json() == {
        'items': [],
        'total': 0,
        'page': 1,
        'page_size': 10,
        'pages': 0,
    }


@pytest.mark.asyncio
async def test_get_ai_history_ticket_not_found(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    configure_history_session(mock_session, user, None)

    response = await client.get(
        '/api/v1/tickets/999/analyses',
        headers=auth_headers(user),
    )

    assert response.status_code == 404
    mock_session.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_ai_history_without_token(
    client: AsyncClient,
    mock_session,
):
    response = await client.get(
        '/api/v1/tickets/10/analyses',
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_ai_history_inactive_user(
    client: AsyncClient,
    mock_session,
):
    user = make_user(active=False)

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_ai_history_invalid_ticket_id(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    response = await client.get(
        '/api/v1/tickets/0/analyses',
        headers=auth_headers(user),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('page', 'page_size'),
    [
        (0, 10),
        (1, 0),
        (1, 101),
    ],
)
async def test_get_ai_history_invalid_pagination(
    client: AsyncClient,
    mock_session,
    page: int,
    page_size: int,
):
    user = make_user()

    # A autenticação precisa retornar um usuário válido
    # antes da validação dos parâmetros de paginação.
    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
        params={
            'page': page,
            'page_size': page_size,
        },
    )

    assert response.status_code == 422

    # A requisição não deve consultar o histórico
    # quando os parâmetros forem inválidos.
    mock_session.execute.assert_awaited_once()
    mock_session.scalar.assert_not_awaited()
    mock_session.commit.assert_not_awaited()
    mock_session.add.assert_not_called()
    mock_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_ai_history_other_user_allowed(
    client: AsyncClient,
    mock_session,
):
    user = make_user(user_id=1)
    analysis = make_analysis(
        analysis_id=5,
        analyzed_by_id=99,
    )

    configure_history_session(
        mock_session,
        user,
        10,
        [analysis],
    )

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()['items'][0]['analyzed_by_id'] == 99


@pytest.mark.asyncio
async def test_get_ai_history_pagination(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    analyses = [
        make_analysis(8),
        make_analysis(7),
    ]

    configure_history_session(
        mock_session,
        user,
        10,
        analyses,
    )

    # Simular oito registros no total.
    mock_session.scalar.return_value = 8

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
        params={
            'page': 2,
            'page_size': 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 8
    assert data['page'] == 2
    assert data['page_size'] == 2
    assert data['pages'] == 4
    assert len(data['items']) == 2

    # Conferir offset e limit da consulta.
    history_statement = mock_session.execute.await_args_list[-1].args[0]
    compiled = history_statement.compile()

    assert 2 in compiled.params.values()


@pytest.mark.asyncio
async def test_get_ai_history_sql_ordering_and_pagination(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    configure_history_session(mock_session, user, 10, [])

    mock_session.scalar.return_value = 25

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
        params={
            'page': 3,
            'page_size': 5,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data['total'] == 25
    assert data['page'] == 3
    assert data['page_size'] == 5
    assert data['pages'] == 5
    assert data['items'] == []

    statement = mock_session.execute.await_args_list[-1].args[0]

    compiled = statement.compile(
        compile_kwargs={'literal_binds': True},
    )
    sql = str(compiled).lower()

    assert 'order by' in sql
    assert 'created_at desc' in sql
    assert 'id desc' in sql
    assert 'limit 5' in sql
    assert 'offset 10' in sql

    mock_session.commit.assert_not_awaited()
    mock_session.add.assert_not_called()
    mock_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_ai_history_page_beyond_total(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    configure_history_session(mock_session, user, 10, [])

    mock_session.scalar.return_value = 3

    response = await client.get(
        '/api/v1/tickets/10/analyses',
        headers=auth_headers(user),
        params={
            'page': 5,
            'page_size': 2,
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        'items': [],
        'total': 3,
        'page': 5,
        'page_size': 2,
        'pages': 2,
    }

    mock_session.commit.assert_not_awaited()
    mock_session.add.assert_not_called()
    mock_session.delete.assert_not_awaited()
