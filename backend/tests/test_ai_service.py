from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError
from prometheus_client import CollectorRegistry

from app.core.ai_metrics import AIMetrics
from app.core.settings import Settings
from app.models.ticket import TicketPriority
from app.schemas.ai import AIClassification, AITicketCategory
from app.services.ai_service import (
    CLASSIFICATION_INSTRUCTIONS,
    AIService,
    AIServiceError,
)


@pytest.fixture
def ai_settings():
    return Settings(
        DATABASE_URL='sqlite+aiosqlite:///:memory:',
        JWT_SECRET_KEY='test-secret',
        OPENAI_MODEL='test-model',
    )


@pytest.fixture
def ai_client():
    client = MagicMock()
    client.responses.parse = AsyncMock()
    return client


@pytest.fixture
def ai_service(ai_client, ai_settings):
    return AIService(client=ai_client, settings=ai_settings)


def make_classification():
    return AIClassification(
        suggested_priority=TicketPriority.HIGH,
        suggested_category=AITicketCategory.NETWORK,
        reason='Falha de conectividade.',
    )


@pytest.mark.asyncio
async def test_ai_service_success(ai_service, ai_client):
    classification = make_classification()

    ai_client.responses.parse.return_value = SimpleNamespace(
        output_parsed=classification,
    )

    result = await ai_service.analyze_ticket(
        title='Sem internet',
        description='Computador não conecta à rede.',
    )

    assert result == classification
    ai_client.responses.parse.assert_awaited_once()

    kwargs = ai_client.responses.parse.await_args.kwargs

    assert kwargs['model'] == 'test-model'
    assert kwargs['instructions'] == CLASSIFICATION_INSTRUCTIONS
    assert kwargs['text_format'] is AIClassification
    assert kwargs['store'] is False
    assert kwargs['timeout'] == ai_service.settings.AI_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_ai_service_success_observability(
    ai_service,
    ai_client,
    caplog,
):
    classification = make_classification()

    ai_client.responses.parse.return_value = SimpleNamespace(
        output_parsed=classification,
    )

    with caplog.at_level('INFO', logger='uvicorn.error'):
        result = await ai_service.analyze_ticket(
            title='Título confidencial',
            description='Descrição confidencial',
        )

    assert result == classification

    events = [
        record
        for record in caplog.records
        if 'ai_classification_completed' in record.getMessage()
    ]

    assert len(events) == 1

    message = events[0].getMessage()

    assert 'outcome=success' in message
    assert 'duration_ms=' in message
    assert 'model=test-model' in message
    assert 'prompt_version=v3' in message
    duration_field = next(
        field for field in message.split() if field.startswith('duration_ms=')
    )

    duration_ms = float(duration_field.split('=', 1)[1])

    assert duration_ms >= 0

    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text
    assert 'Falha de conectividade.' not in caplog.text


@pytest.mark.asyncio
async def test_ai_service_timeout_observability(
    ai_service,
    ai_client,
    caplog,
):
    ai_client.responses.parse.side_effect = APITimeoutError(
        request=MagicMock(),
    )

    with caplog.at_level('INFO', logger='uvicorn.error'):
        with pytest.raises(
            AIServiceError,
            match='Tempo limite excedido',
        ):
            await ai_service.analyze_ticket(
                title='Título confidencial',
                description='Descrição confidencial',
            )

    events = [
        record
        for record in caplog.records
        if 'ai_classification_completed' in record.getMessage()
    ]

    assert len(events) == 1

    message = events[0].getMessage()

    assert 'outcome=error' in message
    assert 'duration_ms=' in message
    assert 'model=test-model' in message
    assert 'prompt_version=v3' in message
    assert 'error_category=timeout' in message

    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text


@pytest.mark.asyncio
async def test_ai_service_connection_observability(
    ai_service,
    ai_client,
    caplog,
):
    ai_client.responses.parse.side_effect = APIConnectionError(
        request=MagicMock(),
    )

    with caplog.at_level('INFO', logger='uvicorn.error'):
        with pytest.raises(
            AIServiceError,
            match='Não foi possível conectar',
        ):
            await ai_service.analyze_ticket(
                title='Título confidencial',
                description='Descrição confidencial',
            )

    events = [
        record
        for record in caplog.records
        if 'ai_classification_completed' in record.getMessage()
    ]

    assert len(events) == 1

    message = events[0].getMessage()

    assert 'outcome=error' in message
    assert 'error_category=connection' in message
    assert 'duration_ms=' in message
    assert 'model=test-model' in message
    assert 'prompt_version=v3' in message

    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text


@pytest.mark.asyncio
async def test_ai_service_api_status_observability(
    ai_service,
    ai_client,
    caplog,
):
    request = httpx2.Request(
        'POST',
        'https://api.openai.com/v1/responses',
    )

    response = httpx2.Response(
        status_code=429,
        request=request,
    )

    ai_client.responses.parse.side_effect = APIStatusError(
        'Sensitive provider response',
        response=response,
        body=None,
    )

    with caplog.at_level('INFO', logger='uvicorn.error'):
        with pytest.raises(
            AIServiceError,
            match='O serviço de IA retornou um erro',
        ):
            await ai_service.analyze_ticket(
                title='Título confidencial',
                description='Descrição confidencial',
            )

    events = [
        record
        for record in caplog.records
        if 'ai_classification_completed' in record.getMessage()
    ]

    assert len(events) == 1

    message = events[0].getMessage()

    assert 'outcome=error' in message
    assert 'error_category=api_status' in message
    assert 'http_status=429' in message
    assert 'duration_ms=' in message
    assert 'model=test-model' in message
    assert 'prompt_version=v3' in message

    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text
    assert 'Sensitive provider response' not in caplog.text


@pytest.mark.asyncio
async def test_ai_service_unexpected_error_observability(
    ai_service,
    ai_client,
    caplog,
):
    ai_client.responses.parse.side_effect = RuntimeError(
        'Sensitive provider details',
    )

    with caplog.at_level('INFO', logger='uvicorn.error'):
        with pytest.raises(
            AIServiceError,
            match='Não foi possível analisar o chamado',
        ):
            await ai_service.analyze_ticket(
                title='Título confidencial',
                description='Descrição confidencial',
            )

    events = [
        record
        for record in caplog.records
        if 'ai_classification_completed' in record.getMessage()
    ]

    assert len(events) == 1

    message = events[0].getMessage()

    assert 'outcome=error' in message
    assert 'error_category=unexpected' in message
    assert 'duration_ms=' in message
    assert 'model=test-model' in message
    assert 'prompt_version=v3' in message

    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text
    assert 'Sensitive provider details' not in caplog.text


@pytest.mark.asyncio
async def test_ai_service_invalid_response_observability(
    ai_service,
    ai_client,
    caplog,
):
    ai_client.responses.parse.return_value = SimpleNamespace(
        output_parsed=None,
    )

    with caplog.at_level('INFO', logger='uvicorn.error'):
        with pytest.raises(
            AIServiceError,
            match='A IA não retornou uma classificação válida',
        ):
            await ai_service.analyze_ticket(
                title='Título confidencial',
                description='Descrição confidencial',
            )

    events = [
        record
        for record in caplog.records
        if 'ai_classification_completed' in record.getMessage()
    ]

    assert len(events) == 1

    message = events[0].getMessage()

    assert 'outcome=error' in message
    assert 'error_category=invalid_response' in message
    assert 'duration_ms=' in message
    assert 'model=test-model' in message
    assert 'prompt_version=v3' in message

    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('title', 'description'),
    [
        ('', 'Descrição válida'),
        ('   ', 'Descrição válida'),
        ('Título válido', ''),
        ('Título válido', '   '),
    ],
)
async def test_ai_service_invalid_input(
    ai_service,
    ai_client,
    title,
    description,
):
    with pytest.raises(
        ValueError,
        match='Título e descrição são obrigatórios',
    ):
        await ai_service.analyze_ticket(title, description)

    ai_client.responses.parse.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_service_description_too_long(
    ai_service,
    ai_client,
):
    with pytest.raises(
        ValueError,
        match='Descrição excede o limite permitido',
    ):
        await ai_service.analyze_ticket(
            title='Título válido',
            description='a' * 4001,
        )

    ai_client.responses.parse.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_service_provider_error(
    ai_service,
    ai_client,
):
    ai_client.responses.parse.side_effect = RuntimeError(
        'Provider unavailable'
    )

    with pytest.raises(AIServiceError):
        await ai_service.analyze_ticket(
            title='Erro no sistema',
            description='Aplicação indisponível.',
        )


@pytest.mark.asyncio
async def test_ai_service_empty_response(
    ai_service,
    ai_client,
):
    ai_client.responses.parse.return_value = SimpleNamespace(
        output_parsed=None,
    )

    with pytest.raises(AIServiceError):
        await ai_service.analyze_ticket(
            title='Erro no sistema',
            description='Aplicação indisponível.',
        )


@pytest.mark.asyncio
async def test_ai_service_title_too_long(
    ai_service,
    ai_client,
):
    with pytest.raises(
        ValueError,
        match='Título excede o limite permitido',
    ):
        await ai_service.analyze_ticket(
            title='a' * 201,
            description='Descrição válida.',
        )

    ai_client.responses.parse.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_service_timeout(
    ai_service,
    ai_client,
):

    ai_client.responses.parse.side_effect = APITimeoutError(
        request=MagicMock(),
    )

    with pytest.raises(
        AIServiceError,
        match='Tempo limite excedido',
    ):
        await ai_service.analyze_ticket(
            title='Sistema lento',
            description='Sistema não responde.',
        )


@pytest.mark.asyncio
async def test_ai_service_connection_error(
    ai_service,
    ai_client,
):

    ai_client.responses.parse.side_effect = APIConnectionError(
        request=MagicMock(),
    )

    with pytest.raises(
        AIServiceError,
        match='Não foi possível conectar',
    ):
        await ai_service.analyze_ticket(
            title='Erro de rede',
            description='Aplicação indisponível.',
        )


@pytest.mark.asyncio
async def test_ai_service_api_status_error(
    ai_service,
    ai_client,
):

    request = httpx2.Request(
        'POST',
        'https://api.openai.com/v1/responses',
    )

    response = httpx2.Response(
        status_code=429,
        request=request,
    )

    ai_client.responses.parse.side_effect = APIStatusError(
        'Rate limit exceeded',
        response=response,
        body=None,
    )

    with pytest.raises(
        AIServiceError,
        match='O serviço de IA retornou um erro',
    ):
        await ai_service.analyze_ticket(
            title='Falha no sistema',
            description='Sistema indisponível.',
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('exception', 'expected_message'),
    [
        (
            APITimeoutError(request=MagicMock()),
            'categoria=timeout',
        ),
        (
            APIConnectionError(request=MagicMock()),
            'categoria=connection',
        ),
        (
            RuntimeError('Sensitive provider details'),
            'categoria=unexpected',
        ),
    ],
)
async def test_ai_service_safe_error_logging(
    ai_service,
    ai_client,
    caplog,
    exception,
    expected_message,
):
    ai_client.responses.parse.side_effect = exception

    with pytest.raises(AIServiceError):
        await ai_service.analyze_ticket(
            title='Título confidencial',
            description='Descrição confidencial',
        )

    assert expected_message in caplog.text
    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text
    assert 'Sensitive provider details' not in caplog.text


@pytest.mark.asyncio
async def test_ai_service_safe_http_status_logging(
    ai_service,
    ai_client,
    caplog,
):
    request = httpx2.Request(
        'POST',
        'https://api.openai.com/v1/responses',
    )

    response = httpx2.Response(
        status_code=429,
        request=request,
    )

    ai_client.responses.parse.side_effect = APIStatusError(
        'Sensitive provider response',
        response=response,
        body=None,
    )

    with pytest.raises(AIServiceError):
        await ai_service.analyze_ticket(
            title='Título confidencial',
            description='Descrição confidencial',
        )

    assert 'categoria=api_status status=429' in caplog.text
    assert 'Sensitive provider response' not in caplog.text
    assert 'Título confidencial' not in caplog.text
    assert 'Descrição confidencial' not in caplog.text


def test_classification_instructions_define_priorities():
    instructions = CLASSIFICATION_INSTRUCTIONS

    for priority in ('low', 'medium', 'high', 'critical'):
        assert f'Use {priority} para' in instructions


def test_classification_instructions_consider_impact():
    instructions = CLASSIFICATION_INSTRUCTIONS

    assert 'alcance' in instructions
    assert 'interrupção' in instructions
    assert 'alternativas' in instructions
    assert 'urgência' in instructions


def test_classification_instructions_avoid_priority_escalation():
    instructions = CLASSIFICATION_INSTRUCTIONS

    assert 'não determina automaticamente' in instructions
    assert 'não presuma consequências adicionais' in instructions


def test_classification_instructions_define_medium_with_alternative():
    instructions = CLASSIFICATION_INSTRUCTIONS

    assert 'funcionalidades relevantes degradadas' in instructions
    assert 'vários usuários' in instructions
    assert 'alternativa operacional' in instructions


def test_classification_instructions_define_critical_operations():
    instructions = CLASSIFICATION_INSTRUCTIONS

    assert 'paralisação completa de operação essencial' in instructions
    assert 'sem alternativa operacional viável' in instructions


def test_classification_instructions_avoid_automatic_escalation():
    instructions = CLASSIFICATION_INSTRUCTIONS

    assert 'não determina automaticamente' in instructions
    assert 'Não reduza a prioridade apenas' in instructions


@pytest.mark.asyncio
async def test_ai_service_records_success_metrics(
    ai_client,
    ai_settings,
):
    registry = CollectorRegistry()
    metrics = AIMetrics(registry=registry)

    service = AIService(
        client=ai_client,
        settings=ai_settings,
        metrics=metrics,
    )

    classification = make_classification()

    ai_client.responses.parse.return_value = SimpleNamespace(
        output_parsed=classification,
    )

    result = await service.analyze_ticket(
        title='Sem internet',
        description='Computador não conecta à rede.',
    )

    assert result == classification

    labels = {
        'outcome': 'success',
        'model': 'test-model',
        'prompt_version': 'v3',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_ai_classifications_total',
            labels,
        )
        == 1
    )

    assert (
        registry.get_sample_value(
            'smartdesk_ai_classification_duration_seconds_count',
            labels,
        )
        == 1
    )

    duration = registry.get_sample_value(
        'smartdesk_ai_classification_duration_seconds_sum',
        labels,
    )

    assert duration is not None
    assert duration >= 0

    assert (
        registry.get_sample_value(
            'smartdesk_ai_errors_total',
            {
                'error_category': 'timeout',
                'model': 'test-model',
                'prompt_version': 'v3',
            },
        )
        is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('error_category', 'exception'),
    [
        (
            'timeout',
            APITimeoutError(request=MagicMock()),
        ),
        (
            'connection',
            APIConnectionError(request=MagicMock()),
        ),
        (
            'api_status',
            APIStatusError(
                message='Erro simulado',
                response=httpx2.Response(
                    429,
                    request=httpx2.Request(
                        'POST',
                        'https://example.com',
                    ),
                ),
                body=None,
            ),
        ),
        (
            'unexpected',
            RuntimeError('Erro simulado'),
        ),
        (
            'invalid_response',
            None,
        ),
    ],
)
async def test_ai_service_records_error_metrics(
    ai_client,
    ai_settings,
    error_category,
    exception,
):
    registry = CollectorRegistry()
    metrics = AIMetrics(registry=registry)

    service = AIService(
        client=ai_client,
        settings=ai_settings,
        metrics=metrics,
    )

    if exception is None:
        ai_client.responses.parse.return_value = SimpleNamespace(
            output_parsed=None,
        )
    else:
        ai_client.responses.parse.side_effect = exception

    with pytest.raises(AIServiceError):
        await service.analyze_ticket(
            title='Falha simulada',
            description='Descrição de teste',
        )

    labels = {
        'outcome': 'error',
        'model': 'test-model',
        'prompt_version': 'v3',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_ai_classifications_total',
            labels,
        )
        == 1
    )

    assert (
        registry.get_sample_value(
            'smartdesk_ai_classification_duration_seconds_count',
            labels,
        )
        == 1
    )

    assert (
        registry.get_sample_value(
            'smartdesk_ai_errors_total',
            {
                'error_category': error_category,
                'model': 'test-model',
                'prompt_version': 'v3',
            },
        )
        == 1
    )

    assert (
        registry.get_sample_value(
            'smartdesk_ai_classifications_total',
            {
                'outcome': 'success',
                'model': 'test-model',
                'prompt_version': 'v3',
            },
        )
        is None
    )
