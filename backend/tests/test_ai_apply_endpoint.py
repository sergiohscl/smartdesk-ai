from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.ai_analysis import AIAnalysis
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole


def make_user(
    role: UserRole = UserRole.USER,
    user_id: int = 1,
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


def make_ticket(
    owner_id: int = 1,
    ticket_id: int = 10,
    priority: TicketPriority = TicketPriority.MEDIUM,
) -> Ticket:
    now = datetime.now(UTC)

    return Ticket(
        id=ticket_id,
        title='Computador não liga',
        description='O computador não inicia.',
        status=TicketStatus.OPEN,
        priority=priority,
        created_by_id=owner_id,
        created_at=now,
        updated_at=now,
    )


def make_analysis(
    ticket_id: int = 10,
    analysis_id: int = 15,
    priority: TicketPriority = TicketPriority.HIGH,
    applied: bool = False,
) -> AIAnalysis:
    return AIAnalysis(
        id=analysis_id,
        ticket_id=ticket_id,
        suggested_priority=priority,
        suggested_category='hardware',
        reason='Possível falha física.',
        priority_at_analysis=TicketPriority.MEDIUM,
        analyzed_by_id=1,
        created_at=datetime.now(UTC),
        applied_at=datetime.now(UTC) if applied else None,
        applied_by_id=1 if applied else None,
    )


def configure_session(
    mock_session,
    user: User,
    ticket: Ticket | None,
    analysis: AIAnalysis | None = None,
) -> None:
    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    ticket_result = MagicMock()
    ticket_result.scalar_one_or_none.return_value = ticket

    analysis_result = MagicMock()
    analysis_result.scalar_one_or_none.return_value = analysis

    mock_session.execute.side_effect = [
        auth_result,
        ticket_result,
        analysis_result,
    ]


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {'Authorization': f'Bearer {token}'}


def assert_no_write(mock_session) -> None:
    mock_session.commit.assert_not_awaited()
    mock_session.add.assert_not_called()
    mock_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_ai_analysis_success(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket(owner_id=user.id)
    analysis = make_analysis(ticket_id=ticket.id)

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        f'/api/v1/tickets/{ticket.id}/analyses/{analysis.id}/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data['analysis_id'] == analysis.id
    assert data['ticket_id'] == ticket.id
    assert data['previous_priority'] == 'medium'
    assert data['applied_priority'] == 'high'
    assert data['applied_by_id'] == user.id
    assert datetime.fromisoformat(data['applied_at'])

    assert ticket.priority == TicketPriority.HIGH
    assert analysis.applied_by_id == user.id
    assert analysis.applied_at is not None

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()
    mock_session.add.assert_not_called()
    mock_session.delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'role',
    [UserRole.SUPPORT, UserRole.ADMIN],
)
async def test_apply_ai_analysis_global_access(
    client: AsyncClient,
    mock_session,
    role: UserRole,
):
    user = make_user(role=role)
    ticket = make_ticket(owner_id=99)
    analysis = make_analysis()

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert ticket.priority == TicketPriority.HIGH
    assert analysis.applied_by_id == user.id

    statement = mock_session.execute.await_args_list[1].args[0]
    compiled = statement.compile()

    sql = str(compiled)
    where_sql = sql.split('WHERE', maxsplit=1)[-1]

    # SUPPORT e ADMIN não devem ser limitados
    # ao proprietário do chamado.
    assert 'tickets.id' in where_sql
    assert 'tickets.created_by_id' not in where_sql

    # A consulta deve bloquear o chamado.
    assert 'FOR UPDATE' in sql.upper()

    # O ID solicitado deve estar entre os parâmetros.
    assert ticket.id in compiled.params.values()

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_ai_analysis_without_token(
    client: AsyncClient,
    mock_session,
):
    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
    )

    assert response.status_code == 401
    mock_session.execute.assert_not_awaited()
    assert_no_write(mock_session)


@pytest.mark.asyncio
async def test_apply_ai_analysis_inactive_user(
    client: AsyncClient,
    mock_session,
):
    user = make_user(active=False)

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 403
    mock_session.execute.assert_awaited_once()
    assert_no_write(mock_session)


@pytest.mark.asyncio
async def test_apply_ai_analysis_other_user_forbidden(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    configure_session(mock_session, user, None)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()['detail'] == 'Chamado não encontrado.'

    statement = mock_session.execute.await_args_list[1].args[0]
    compiled = statement.compile()

    assert 'tickets.created_by_id' in str(compiled)
    assert user.id in compiled.params.values()

    assert mock_session.execute.await_count == 2
    assert_no_write(mock_session)


@pytest.mark.asyncio
async def test_apply_ai_analysis_ticket_not_found(
    client: AsyncClient,
    mock_session,
):
    user = make_user(role=UserRole.ADMIN)
    configure_session(mock_session, user, None)

    response = await client.post(
        '/api/v1/tickets/999/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 404
    assert mock_session.execute.await_count == 2
    assert_no_write(mock_session)


@pytest.mark.asyncio
async def test_apply_ai_analysis_not_found(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    configure_session(mock_session, user, ticket, None)

    response = await client.post(
        '/api/v1/tickets/10/analyses/999/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()['detail'] == (
        'Análise não encontrada para este chamado.'
    )

    assert ticket.priority == TicketPriority.MEDIUM
    assert_no_write(mock_session)


@pytest.mark.asyncio
async def test_apply_ai_analysis_already_applied(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    analysis = make_analysis(applied=True)

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Esta análise já foi aplicada.'

    assert ticket.priority == TicketPriority.MEDIUM
    assert analysis.applied_by_id == 1
    assert_no_write(mock_session)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('ticket_id', 'analysis_id'),
    [(0, 15), (-1, 15), (10, 0), (10, -1)],
)
async def test_apply_ai_analysis_invalid_ids(
    client: AsyncClient,
    mock_session,
    ticket_id: int,
    analysis_id: int,
):
    user = make_user()

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    response = await client.post(
        f'/api/v1/tickets/{ticket_id}/analyses/{analysis_id}/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 422
    mock_session.execute.assert_awaited_once()
    assert_no_write(mock_session)


@pytest.mark.asyncio
async def test_apply_ai_analysis_same_priority(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket(priority=TicketPriority.HIGH)
    analysis = make_analysis(priority=TicketPriority.HIGH)

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()['previous_priority'] == 'high'
    assert response.json()['applied_priority'] == 'high'

    assert analysis.applied_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_ai_analysis_commit_failure(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    analysis = make_analysis()

    configure_session(mock_session, user, ticket, analysis)

    mock_session.commit.side_effect = RuntimeError(
        'Falha simulada no banco.'
    )

    with pytest.raises(RuntimeError, match='Falha simulada'):
        await client.post(
            '/api/v1/tickets/10/analyses/15/apply',
            headers=auth_headers(user),
        )

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_awaited_once()
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_apply_ai_analysis_row_locking(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    analysis = make_analysis()

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert mock_session.execute.await_count == 3

    ticket_statement = mock_session.execute.await_args_list[1].args[0]
    analysis_statement = mock_session.execute.await_args_list[2].args[0]

    assert 'FOR UPDATE' in str(ticket_statement.compile()).upper()
    assert 'FOR UPDATE' in str(analysis_statement.compile()).upper()

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_ai_analysis_filters_by_ticket(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    analysis = make_analysis()

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    statement = mock_session.execute.await_args_list[2].args[0]
    compiled = statement.compile()
    sql = str(compiled)

    assert 'ai_analyses.id' in sql
    assert 'ai_analyses.ticket_id' in sql
    assert analysis.id in compiled.params.values()
    assert ticket.id in compiled.params.values()


@pytest.mark.asyncio
async def test_apply_ai_analysis_lock_order(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    analysis = make_analysis()

    configure_session(mock_session, user, ticket, analysis)

    response = await client.post(
        '/api/v1/tickets/10/analyses/15/apply',
        headers=auth_headers(user),
    )

    assert response.status_code == 200

    statements = [
        str(call.args[0].compile()).upper()
        for call in mock_session.execute.await_args_list
    ]

    assert 'FROM TICKETS' in statements[1]
    assert 'FROM AI_ANALYSES' in statements[2]

    assert 'FOR UPDATE' in statements[1]
    assert 'FOR UPDATE' in statements[2]

    mock_session.commit.assert_awaited_once()
