from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.core.ai_dependencies import get_ai_service
from app.core.security import create_access_token
from app.core.settings import get_settings
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ai import AIClassification, AITicketCategory
from app.services.ai_service import AIServiceError


def make_user(role=UserRole.USER, user_id=1, active=True):
    return User(
        id=user_id,
        name='Usuário Teste',
        email=f'user{user_id}@teste.com',
        hashed_password='hashed-password',
        is_active=active,
        role=role,
        created_at=datetime.now(UTC),
    )


def make_ticket(owner_id=1, ticket_id=10):
    now = datetime.now(UTC)

    return Ticket(
        id=ticket_id,
        title='Computador não liga',
        description='O computador não inicia.',
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        created_by_id=owner_id,
        created_at=now,
        updated_at=now,
    )


def configure_session(mock_session, user, ticket=None):
    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user

    ticket_result = MagicMock()
    ticket_result.scalar_one_or_none.return_value = ticket

    mock_session.execute.side_effect = [
        auth_result,
        ticket_result,
    ]


def configure_analysis_id(mock_session, analysis_id=15):
    def assign_analysis_id(analysis):
        assert isinstance(analysis, AIAnalysis)
        analysis.id = analysis_id

    mock_session.add.side_effect = assign_analysis_id


@pytest.fixture
def mock_ai_service():
    service = MagicMock()
    service.analyze_ticket = AsyncMock(
        return_value=AIClassification(
            suggested_priority=TicketPriority.HIGH,
            suggested_category=AITicketCategory.HARDWARE,
            reason='Possível falha física no computador.',
        )
    )

    app.dependency_overrides[get_ai_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_ai_service, None)


@pytest.mark.asyncio
async def test_analyze_own_ticket_success(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user()
    ticket = make_ticket(owner_id=user.id)
    configure_session(mock_session, user, ticket)
    configure_analysis_id(mock_session)

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        f'/api/v1/tickets/{ticket.id}/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200

    data = response.json()

    assert data['ticket_id'] == ticket.id
    assert data['suggested_priority'] == 'high'
    assert data['suggested_category'] == 'hardware'
    assert data['reason'] == 'Possível falha física no computador.'
    assert data['analysis_id'] == 15

    mock_ai_service.analyze_ticket.assert_awaited_once_with(
        title=ticket.title,
        description=ticket.description,
    )

    # Verificar persistência da análise.
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()
    mock_session.delete.assert_not_awaited()

    # Inspecionar o objeto enviado para persistência.
    saved_analysis = mock_session.add.call_args.args[0]

    assert isinstance(saved_analysis, AIAnalysis)
    assert saved_analysis.ticket_id == ticket.id
    assert saved_analysis.suggested_priority == TicketPriority.HIGH
    assert saved_analysis.suggested_category == 'hardware'
    assert saved_analysis.reason == ('Possível falha física no computador.')
    assert saved_analysis.priority_at_analysis == TicketPriority.MEDIUM
    assert saved_analysis.analyzed_by_id == user.id

    # A análise ainda não foi aplicada ao chamado.
    assert saved_analysis.applied_at is None
    assert saved_analysis.applied_by_id is None

    # A prioridade original deve permanecer inalterada.
    assert ticket.priority == TicketPriority.MEDIUM
    assert saved_analysis.id == data['analysis_id']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'role',
    [UserRole.SUPPORT, UserRole.ADMIN],
)
async def test_analyze_ticket_global_access(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
    role,
):
    user = make_user(role=role)
    ticket = make_ticket(owner_id=99)
    configure_session(mock_session, user, ticket)
    configure_analysis_id(mock_session)

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        f'/api/v1/tickets/{ticket.id}/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    data = response.json()

    assert data['analysis_id'] == 15
    mock_ai_service.analyze_ticket.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_ticket_not_found(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user()
    configure_session(mock_session, user, None)

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets/999/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 404
    mock_ai_service.analyze_ticket.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_ticket_without_token(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    response = await client.post(
        '/api/v1/tickets/10/analyze',
    )

    assert response.status_code == 401
    mock_ai_service.analyze_ticket.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_ticket_inactive_user(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user(active=False)

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets/10/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 403
    mock_ai_service.analyze_ticket.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_ticket_invalid_id(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user()

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = auth_result

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets/0/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 422
    mock_ai_service.analyze_ticket.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_ticket_ai_service_error(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user()
    ticket = make_ticket()
    configure_session(mock_session, user, ticket)

    mock_ai_service.analyze_ticket.side_effect = AIServiceError(
        'Falha no provedor.'
    )

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        '/api/v1/tickets/10/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 503
    assert response.json()['detail'] == (
        'Serviço de análise com IA indisponível.'
    )


@pytest.mark.asyncio
async def test_analyze_ticket_other_user_forbidden(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user(
        role=UserRole.USER,
        user_id=1,
    )
    ticket = make_ticket(
        owner_id=99,
        ticket_id=10,
    )

    configure_session(mock_session, user, ticket)

    token = create_access_token(subject=str(user.id))

    response = await client.post(
        f'/api/v1/tickets/{ticket.id}/analyze',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == (
        'Você não tem permissão para analisar este chamado.'
    )

    # A autorização deve ser verificada antes da análise.
    mock_ai_service.analyze_ticket.assert_not_awaited()

    # Nenhuma análise deve ser gravada no banco.
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_not_awaited()
    mock_session.delete.assert_not_awaited()

    # O chamado original permanece inalterado.
    assert ticket.priority == TicketPriority.MEDIUM


@pytest.mark.asyncio
async def test_analyze_ticket_missing_api_key(
    client: AsyncClient,
    mock_session,
):
    user = make_user()
    ticket = make_ticket()
    configure_session(mock_session, user, ticket)

    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={'OPENAI_API_KEY': None}
    )

    try:
        token = create_access_token(subject=str(user.id))

        response = await client.post(
            '/api/v1/tickets/10/analyze',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert response.status_code == 503
        assert response.json()['detail'] == (
            'Serviço de análise com IA indisponível.'
        )
        mock_session.commit.assert_not_awaited()
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_analyze_ticket_not_found_before_ai_initialization(
    client: AsyncClient,
    mock_session,
):
    user = make_user(user_id=1)
    configure_session(mock_session, user, None)

    dependency_called = False

    def override_ai_service():
        nonlocal dependency_called
        dependency_called = True
        raise AssertionError('A IA não deveria ser inicializada.')

    app.dependency_overrides[get_ai_service] = override_ai_service

    try:
        token = create_access_token(subject=str(user.id))

        response = await client.post(
            '/api/v1/tickets/10/analyze',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert response.status_code == 404
        assert dependency_called is False
    finally:
        app.dependency_overrides.pop(get_ai_service, None)


@pytest.mark.asyncio
async def test_analyze_ticket_database_commit_failure(
    client: AsyncClient,
    mock_session,
    mock_ai_service,
):
    user = make_user()
    ticket = make_ticket(owner_id=user.id)

    configure_session(mock_session, user, ticket)

    mock_session.commit.side_effect = RuntimeError('Falha simulada no banco.')

    token = create_access_token(subject=str(user.id))

    with pytest.raises(RuntimeError, match='Falha simulada'):
        await client.post(
            f'/api/v1/tickets/{ticket.id}/analyze',
            headers={'Authorization': f'Bearer {token}'},
        )

    mock_ai_service.analyze_ticket.assert_awaited_once()
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_awaited_once()

    saved_analysis = mock_session.add.call_args.args[0]

    assert isinstance(saved_analysis, AIAnalysis)
    assert saved_analysis.ticket_id == ticket.id
    assert saved_analysis.analyzed_by_id == user.id

    # A recomendação não altera automaticamente o chamado.
    assert ticket.priority == TicketPriority.MEDIUM
