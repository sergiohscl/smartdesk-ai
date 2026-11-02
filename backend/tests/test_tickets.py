from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User


def make_user() -> User:
    return User(
        id=1,
        name='Usuario Teste',
        email='usuario@teste.com',
        hashed_password='hashed-password',
        is_active=True,
        created_at=datetime.now(UTC),
    )


def mock_authenticated_user(mock_session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = result


@pytest.mark.asyncio
async def test_create_ticket_success(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    mock_authenticated_user(mock_session, user)

    async def refresh_ticket(ticket):
        ticket.id = 1
        ticket.status = TicketStatus.OPEN
        ticket.created_at = datetime.now(UTC)
        ticket.updated_at = datetime.now(UTC)

    mock_session.refresh.side_effect = refresh_ticket

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': 'Computador não liga',
            'description': 'O computador não inicia.',
            'priority': 'high',
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data['id'] == 1
    assert data['title'] == 'Computador não liga'
    assert data['status'] == 'open'
    assert data['priority'] == 'high'
    assert data['created_by_id'] == user.id

    mock_session.add.assert_called_once()

    created_ticket = mock_session.add.call_args.args[0]

    assert created_ticket.created_by_id == user.id
    assert created_ticket.priority == TicketPriority.HIGH

    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(created_ticket)


@pytest.mark.asyncio
async def test_create_ticket_without_token(
    client: AsyncClient,
    mock_session,
):
    response = await client.post(
        '/api/v1/tickets',
        json={
            'title': 'Computador não liga',
            'description': 'O computador não inicia.',
        },
    )

    assert response.status_code == 401
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_ticket_invalid_data(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    mock_authenticated_user(mock_session, user)

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': 'PC',
            'description': 'Erro',
            'priority': 'high',
        },
    )

    assert response.status_code == 422
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_ticket_inactive_user(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    user.is_active = False

    mock_authenticated_user(mock_session, user)

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': 'Computador não liga',
            'description': 'O computador não inicia.',
        },
    )

    assert response.status_code == 403
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_tickets_success(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    now = datetime.now(UTC)

    tickets = [
        Ticket(
            id=1,
            title='Computador não liga',
            description='O computador não inicia.',
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            created_by_id=user.id,
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            id=2,
            title='Erro de conexão',
            description='Sem acesso à rede.',
            status=TicketStatus.IN_PROGRESS,
            priority=TicketPriority.MEDIUM,
            created_by_id=user.id,
            created_at=now,
            updated_at=now,
        ),
    ]

    # Resultado da autenticação JWT
    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    # Resultado da listagem de chamados
    tickets_result = MagicMock()
    tickets_result.scalars.return_value.all.return_value = tickets

    # Primeira consulta: autenticação
    # Segunda consulta: listagem
    mock_session.execute.side_effect = [
        auth_result,
        tickets_result,
    ]

    # Total de registros
    mock_session.scalar = AsyncMock(return_value=2)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        '/api/v1/tickets',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 2
    assert data['page'] == 1
    assert data['page_size'] == 10
    assert data['pages'] == 1

    assert len(data['items']) == 2

    assert data['items'][0]['id'] == 1
    assert data['items'][0]['title'] == 'Computador não liga'
    assert data['items'][0]['status'] == 'open'
    assert data['items'][0]['priority'] == 'high'

    assert data['items'][1]['id'] == 2
    assert data['items'][1]['title'] == 'Erro de conexão'
    assert data['items'][1]['status'] == 'in_progress'

    # Verificar consultas
    assert mock_session.execute.await_count == 2
    mock_session.scalar.assert_awaited_once()

    # GET não deve alterar o banco
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_tickets_pagination(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    tickets_result = MagicMock()
    tickets_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        auth_result,
        tickets_result,
    ]

    mock_session.scalar = AsyncMock(return_value=25)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        '/api/v1/tickets?page=2&page_size=10',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 25
    assert data['page'] == 2
    assert data['page_size'] == 10
    assert data['pages'] == 3
    assert data['items'] == []

    # Verificar LIMIT e OFFSET da consulta
    query = mock_session.execute.await_args_list[1].args[0]

    compiled = query.compile()

    assert compiled.params['param_1'] == 10
    assert compiled.params['param_2'] == 10


@pytest.mark.asyncio
async def test_list_tickets_without_token(
    client: AsyncClient,
    mock_session,
):
    response = await client.get('/api/v1/tickets')

    assert response.status_code == 401
    mock_session.scalar.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'params',
    [
        'page=0',
        'page_size=0',
        'page_size=101',
        'page=abc',
    ],
)
async def test_list_tickets_invalid_pagination(
    client: AsyncClient,
    mock_session,
    params: str,
):
    user = make_user()
    mock_authenticated_user(mock_session, user)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        f'/api/v1/tickets?{params}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'params',
    [
        'sort_by=invalid',
        'sort_order=invalid',
    ],
)
async def test_list_tickets_invalid_sort(
    client: AsyncClient,
    mock_session,
    params: str,
):
    user = make_user()
    mock_authenticated_user(mock_session, user)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        f'/api/v1/tickets?{params}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_tickets_filters_by_authenticated_user(
    client: AsyncClient,
    mock_session,
):
    user = make_user()

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    tickets_result = MagicMock()
    tickets_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        auth_result,
        tickets_result,
    ]
    mock_session.scalar = AsyncMock(return_value=0)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        '/api/v1/tickets',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200

    # Verificar execução das consultas
    mock_session.scalar.assert_awaited_once()
    assert mock_session.execute.await_count == 2

    # Recuperar consultas SQL
    count_call = mock_session.scalar.await_args
    list_call = mock_session.execute.await_args_list[1]

    assert count_call is not None

    count_query = count_call.args[0]
    list_query = list_call.args[0]

    # Compilar consultas
    count_compiled = count_query.compile()
    list_compiled = list_query.compile()

    count_sql = str(count_compiled)
    list_sql = str(list_compiled)

    # Verificar filtro por usuário
    assert 'tickets.created_by_id' in count_sql
    assert 'tickets.created_by_id' in list_sql

    # Verificar ID do usuário nos parâmetros
    assert user.id in count_compiled.params.values()
    assert user.id in list_compiled.params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('sort_by', 'sort_order', 'expected_order'),
    [
        ('created_at', 'desc', 'DESC'),
        ('created_at', 'asc', 'ASC'),
        ('title', 'asc', 'ASC'),
        ('priority', 'desc', 'DESC'),
        ('status', 'asc', 'ASC'),
        ('updated_at', 'desc', 'DESC'),
        ('id', 'asc', 'ASC'),
    ],
)
async def test_list_tickets_sorting(
    client: AsyncClient,
    mock_session,
    sort_by: str,
    sort_order: str,
    expected_order: str,
):
    user = make_user()

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    tickets_result = MagicMock()
    tickets_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        auth_result,
        tickets_result,
    ]

    mock_session.scalar = AsyncMock(return_value=0)

    token = create_access_token(subject=str(user.id))

    response = await client.get(
        '/api/v1/tickets',
        params={
            'sort_by': sort_by,
            'sort_order': sort_order,
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200

    assert mock_session.execute.await_count == 2

    query = mock_session.execute.await_args_list[1].args[0]

    sql = str(query.compile())

    assert f'tickets.{sort_by} {expected_order}' in sql

    # Ordenação secundária determinística
    assert 'tickets.id ASC' in sql
