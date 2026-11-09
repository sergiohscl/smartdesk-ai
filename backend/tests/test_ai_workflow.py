from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.core.ai_dependencies import get_ai_service
from app.core.security import create_access_token
from app.main import app
from app.models.ai_analysis import AIAnalysis
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ai import AIClassification, AITicketCategory


def make_workflow_data():
    now = datetime.now(UTC)

    user = User(
        id=1,
        name='Usuário Teste',
        email='user1@teste.com',
        hashed_password='hashed-password',
        is_active=True,
        role=UserRole.USER,
        created_at=now,
    )

    ticket = Ticket(
        id=10,
        title='Computador não liga',
        description='O computador não inicia.',
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        created_by_id=user.id,
        created_at=now,
        updated_at=now,
    )

    ai_service = MagicMock()
    ai_service.analyze_ticket = AsyncMock(
        return_value=AIClassification(
            suggested_priority=TicketPriority.HIGH,
            suggested_category=AITicketCategory.HARDWARE,
            reason='Possível falha física no computador.',
        )
    )

    return user, ticket, ai_service


def assert_initial_history(history, analysis):
    assert history['total'] == 1
    assert len(history['items']) == 1
    assert history['items'][0]['id'] == analysis.id
    assert history['items'][0]['applied_at'] is None
    assert history['items'][0]['applied_by_id'] is None


def assert_updated_history(history, analysis, user):
    assert history['total'] == 1

    item = history['items'][0]

    assert item['id'] == analysis.id
    assert item['suggested_priority'] == 'high'
    assert item['priority_at_analysis'] == 'medium'
    assert item['applied_at'] is not None
    assert item['applied_by_id'] == user.id


def configure_workflow_session(mock_session, user, ticket, analyses):
    def result_with_scalar(value):
        result = MagicMock()
        result.scalar_one_or_none.return_value = value
        return result

    def result_with_analyses():
        result = MagicMock()
        result.scalars.return_value.all.return_value = list(analyses)
        return result

    def add_analysis(analysis):
        assert isinstance(analysis, AIAnalysis)
        assert analysis.ticket_id == ticket.id

        analysis.id = len(analyses) + 1
        analysis.created_at = datetime.now(UTC)
        analyses.append(analysis)

    mock_session.add.side_effect = add_analysis

    execute_results = [
        # Analisar chamado.
        result_with_scalar(user),
        result_with_scalar(ticket),
        # Consultar histórico inicial.
        result_with_scalar(user),
        result_with_scalar(ticket.id),
        result_with_analyses,
        # Aplicar prioridade.
        result_with_scalar(user),
        result_with_scalar(ticket),
        result_with_scalar,
        # Consultar histórico atualizado.
        result_with_scalar(user),
        result_with_scalar(ticket.id),
        result_with_analyses,
        # Tentar aplicar novamente.
        result_with_scalar(user),
        result_with_scalar(ticket),
        result_with_scalar,
    ]

    async def execute_side_effect(statement):
        if not execute_results:
            raise AssertionError(f'Consulta SQL inesperada: {statement}')

        item = execute_results.pop(0)

        if item is result_with_analyses:
            return result_with_analyses()

        if item is result_with_scalar:
            return result_with_scalar(analyses[0])

        return item

    async def count_analyses(statement):
        return len(analyses)

    mock_session.execute.side_effect = execute_side_effect
    mock_session.scalar.side_effect = count_analyses

    return execute_results


@pytest.mark.asyncio
async def test_ai_workflow_analyze_history_apply_and_reapply(
    client: AsyncClient,
    mock_session,
) -> None:

    user, ticket, ai_service = make_workflow_data()

    analyses: list[AIAnalysis] = []

    execute_results = configure_workflow_session(
        mock_session,
        user,
        ticket,
        analyses,
    )

    ai_service = MagicMock()
    ai_service.analyze_ticket = AsyncMock(
        return_value=AIClassification(
            suggested_priority=TicketPriority.HIGH,
            suggested_category=AITicketCategory.HARDWARE,
            reason='Possível falha física no computador.',
        )
    )

    async def count_analyses(statement):
        return len(analyses)

    mock_session.scalar.side_effect = count_analyses

    token = create_access_token(subject=str(user.id))
    headers = {'Authorization': f'Bearer {token}'}

    app.dependency_overrides[get_ai_service] = lambda: ai_service

    try:
        # 1. Analisar o chamado.
        response = await client.post(
            f'/api/v1/tickets/{ticket.id}/analyze',
            headers=headers,
        )

        assert response.status_code == 200, response.text
        assert response.json()['suggested_priority'] == 'high'
        assert ticket.priority == TicketPriority.MEDIUM

        assert len(analyses) == 1

        analysis = analyses[0]

        assert analysis.priority_at_analysis == TicketPriority.MEDIUM
        assert analysis.applied_at is None
        assert analysis.applied_by_id is None

        # 2. Consultar o histórico antes da aplicação.
        response = await client.get(
            f'/api/v1/tickets/{ticket.id}/analyses',
            headers=headers,
        )

        assert response.status_code == 200, response.text

        assert_initial_history(response.json(), analysis)

        # 3. Aplicar a prioridade sugerida.
        response = await client.post(
            (f'/api/v1/tickets/{ticket.id}/analyses/{analysis.id}/apply'),
            headers=headers,
        )

        assert response.status_code == 200, response.text

        applied = response.json()

        assert applied['previous_priority'] == 'medium'
        assert applied['applied_priority'] == 'high'
        assert applied['applied_by_id'] == user.id

        assert ticket.priority == TicketPriority.HIGH
        assert analysis.applied_at is not None
        assert analysis.applied_by_id == user.id

        # 4. Consultar o histórico após a aplicação.
        response = await client.get(
            f'/api/v1/tickets/{ticket.id}/analyses',
            headers=headers,
        )

        assert response.status_code == 200, response.text

        assert_updated_history(response.json(), analysis, user)

        # 5. Impedir reaplicação.
        response = await client.post(
            (f'/api/v1/tickets/{ticket.id}/analyses/{analysis.id}/apply'),
            headers=headers,
        )

        assert response.status_code == 409, response.text

        # 6. Verificações finais.
        ai_service.analyze_ticket.assert_awaited_once_with(
            title=ticket.title,
            description=ticket.description,
        )

        mock_session.add.assert_called_once()
        assert mock_session.commit.await_count == 2
        mock_session.rollback.assert_not_awaited()

        assert not execute_results

    finally:
        app.dependency_overrides.pop(get_ai_service, None)
