import pytest
from pydantic import ValidationError

from app.models.ticket import TicketPriority
from app.schemas.ai import (
    AIAnalysisResponse,
    AIClassification,
    AITicketCategory,
)


def test_ai_classification_success():
    result = AIClassification(
        suggested_priority=TicketPriority.HIGH,
        suggested_category=AITicketCategory.NETWORK,
        reason='Falha de conectividade.',
    )

    assert result.suggested_priority == TicketPriority.HIGH
    assert result.suggested_category == AITicketCategory.NETWORK


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('suggested_priority', 'urgent'),
        ('suggested_category', 'finance'),
        ('reason', ''),
        ('reason', 'a' * 501),
    ],
)
def test_ai_classification_invalid_data(field, value):
    payload = {
        'suggested_priority': 'medium',
        'suggested_category': 'software',
        'reason': 'Erro no aplicativo.',
    }

    payload[field] = value

    with pytest.raises(ValidationError):
        AIClassification.model_validate(payload)


def test_ai_classification_rejects_extra_fields():
    payload = {
        'suggested_priority': 'low',
        'suggested_category': 'hardware',
        'reason': 'Falha no teclado.',
        'unexpected_field': 'value',
    }

    with pytest.raises(ValidationError):
        AIClassification.model_validate(payload)


@pytest.mark.parametrize('ticket_id', [0, -1])
def test_ai_analysis_invalid_ticket_id(ticket_id):
    payload = {
        'ticket_id': ticket_id,
        'suggested_priority': 'high',
        'suggested_category': 'network',
        'reason': 'Falha de conexão.',
    }

    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_ai_analysis_response_success():
    result = AIAnalysisResponse(
        ticket_id=42,
        suggested_priority=TicketPriority.HIGH,
        suggested_category=AITicketCategory.NETWORK,
        reason='Falha de conexão.',
    )

    assert result.ticket_id == 42
    assert result.suggested_priority == TicketPriority.HIGH
    assert result.suggested_category == AITicketCategory.NETWORK
