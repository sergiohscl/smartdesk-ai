from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.core.settings import Settings
from app.models.ticket import TicketPriority
from app.schemas.ai import AIClassification, AITicketCategory
from app.services.ai_service import AIService, AIServiceError


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
    assert kwargs['text_format'] is AIClassification
    assert kwargs['store'] is False
    assert kwargs['timeout'] == ai_service.settings.AI_TIMEOUT_SECONDS


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
