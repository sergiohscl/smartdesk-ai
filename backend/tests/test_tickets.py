from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.ticket import TicketPriority, TicketStatus
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
