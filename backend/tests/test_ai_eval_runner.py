from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ticket import TicketPriority
from app.schemas.ai import AIClassification, AITicketCategory
from app.services.ai_service import AIService, AIServiceError
from evals.runner import EvaluationCase, evaluate_cases


def make_ai_service_mock(
    category: AITicketCategory = AITicketCategory.NETWORK,
    priority: TicketPriority = TicketPriority.HIGH,
) -> AIService:
    service = MagicMock(spec=AIService)

    service.analyze_ticket = AsyncMock(
        return_value=AIClassification(
            suggested_category=category,
            suggested_priority=priority,
            reason='Classificação simulada para avaliação.',
        )
    )

    return cast(AIService, service)


@pytest.mark.asyncio
async def test_evaluate_cases_all_correct():
    service = make_ai_service_mock()

    cases: list[EvaluationCase] = [
        {
            'id': 'AI-EVAL-001',
            'title': 'Falha de rede',
            'description': 'Rede indisponível.',
            'expected_category': 'network',
            'expected_priority': 'high',
        }
    ]

    report = await evaluate_cases(service, cases)
    results = report.results
    metrics = report.metrics

    assert metrics is not None
    assert report.total_cases == 1
    assert report.success_rate == 1.0
    assert report.failures == []
    assert len(results) == 1
    assert results[0].fully_correct is True
    assert (
        results[0].predicted_reason == 'Classificação simulada para avaliação.'
    )
    assert metrics.total == 1
    assert metrics.full_accuracy == 1.0

    mock_analyze = cast(AsyncMock, service.analyze_ticket)

    mock_analyze.assert_awaited_once_with(
        title='Falha de rede',
        description='Rede indisponível.',
    )


@pytest.mark.asyncio
async def test_evaluate_cases_partial_error():
    service = make_ai_service_mock(
        category=AITicketCategory.SOFTWARE,
        priority=TicketPriority.MEDIUM,
    )

    cases: list[EvaluationCase] = [
        {
            'id': 'AI-EVAL-002',
            'title': 'Falha de rede',
            'description': 'Conexão indisponível.',
            'expected_category': 'network',
            'expected_priority': 'medium',
        }
    ]

    report = await evaluate_cases(service, cases)
    results = report.results
    metrics = report.metrics

    assert metrics is not None
    assert report.success_rate == 1.0
    assert report.failures == []
    assert results[0].category_correct is False
    assert results[0].priority_correct is True
    assert metrics.category_accuracy == 0.0
    assert metrics.priority_accuracy == 1.0
    assert metrics.full_accuracy == 0.0


@pytest.mark.asyncio
async def test_evaluate_cases_empty_dataset():
    service = make_ai_service_mock()

    with pytest.raises(
        ValueError,
        match='A avaliação precisa de chamados',
    ):
        await evaluate_cases(service, [])

    mock_analyze = cast(AsyncMock, service.analyze_ticket)

    mock_analyze.assert_not_awaited()


@pytest.mark.asyncio
async def test_evaluate_cases_continues_after_service_error():
    service = make_ai_service_mock()

    classification = AIClassification(
        suggested_category=AITicketCategory.NETWORK,
        suggested_priority=TicketPriority.HIGH,
        reason='Falha de rede.',
    )

    mock_analyze = cast(AsyncMock, service.analyze_ticket)
    mock_analyze.side_effect = [
        AIServiceError('Falha simulada.'),
        classification,
    ]

    cases: list[EvaluationCase] = [
        {
            'id': 'AI-EVAL-001',
            'title': 'Primeiro chamado',
            'description': 'Falha simulada.',
            'expected_category': 'network',
            'expected_priority': 'high',
        },
        {
            'id': 'AI-EVAL-002',
            'title': 'Segundo chamado',
            'description': 'Rede indisponível.',
            'expected_category': 'network',
            'expected_priority': 'high',
        },
    ]

    report = await evaluate_cases(service, cases)

    assert report.total_cases == 2
    assert report.success_rate == 0.5
    assert len(report.results) == 1
    assert report.results[0].case_id == 'AI-EVAL-002'
    assert len(report.failures) == 1
    assert report.failures[0].case_id == 'AI-EVAL-001'
    assert report.failures[0].error_type == 'ai_service_error'
    assert report.metrics is not None
    assert report.metrics.full_accuracy == 1.0
    assert mock_analyze.await_count == 2


@pytest.mark.asyncio
async def test_evaluate_cases_all_fail():
    service = make_ai_service_mock()

    mock_analyze = cast(AsyncMock, service.analyze_ticket)
    mock_analyze.side_effect = AIServiceError('Serviço indisponível.')

    cases: list[EvaluationCase] = [
        {
            'id': 'AI-EVAL-001',
            'title': 'Falha no sistema',
            'description': 'Sistema indisponível.',
            'expected_category': 'software',
            'expected_priority': 'critical',
        }
    ]

    report = await evaluate_cases(service, cases)

    assert report.total_cases == 1
    assert report.success_rate == 0.0
    assert report.results == []
    assert len(report.failures) == 1
    assert report.metrics is None
    mock_analyze.assert_awaited_once()


@pytest.mark.asyncio
async def test_evaluate_cases_unexpected_error_propagates():
    service = make_ai_service_mock()

    mock_analyze = cast(AsyncMock, service.analyze_ticket)
    mock_analyze.side_effect = ValueError('Entrada inválida.')

    cases: list[EvaluationCase] = [
        {
            'id': 'AI-EVAL-001',
            'title': 'Chamado inválido',
            'description': 'Descrição do chamado.',
            'expected_category': 'other',
            'expected_priority': 'low',
        }
    ]

    with pytest.raises(ValueError, match='Entrada inválida'):
        await evaluate_cases(service, cases)

    mock_analyze.assert_awaited_once()
