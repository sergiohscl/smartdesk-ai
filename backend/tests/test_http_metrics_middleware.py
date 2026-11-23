import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.core.http_metrics import HTTPMetrics
from app.core.http_metrics_middleware import HTTPMetricsMiddleware


@pytest.fixture
def registry():
    return CollectorRegistry()


def make_app(registry):
    app = FastAPI()
    metrics = HTTPMetrics(registry=registry)

    app.add_middleware(
        HTTPMetricsMiddleware,
        metrics=metrics,
    )

    @app.get('/api/v1/tickets/{ticket_id}')
    async def get_ticket(ticket_id: int):
        return {'ticket_id': ticket_id}

    @app.get('/api/v1/metrics')
    async def get_metrics():
        return {'status': 'ok'}

    @app.get('/api/v1/error')
    async def get_error():
        raise RuntimeError('Erro simulado')

    return app


@pytest.mark.asyncio
async def test_middleware_records_success(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        response = await client.get('/api/v1/tickets/123')

    assert response.status_code == 200

    labels = {
        'method': 'GET',
        'route': '/api/v1/tickets/{ticket_id}',
        'status_code': '200',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 1
    )

    assert (
        registry.get_sample_value(
            'smartdesk_http_request_duration_seconds_count',
            labels,
        )
        == 1
    )


@pytest.mark.asyncio
async def test_middleware_normalizes_routes(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        await client.get('/api/v1/tickets/123')
        await client.get('/api/v1/tickets/456')

    labels = {
        'method': 'GET',
        'route': '/api/v1/tickets/{ticket_id}',
        'status_code': '200',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 2
    )

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            {
                'method': 'GET',
                'route': '/api/v1/tickets/123',
                'status_code': '200',
            },
        )
        is None
    )


@pytest.mark.asyncio
async def test_middleware_records_404(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        response = await client.get('/api/v1/unknown')

    assert response.status_code == 404

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            {
                'method': 'GET',
                'route': 'unmatched',
                'status_code': '404',
            },
        )
        == 1
    )


@pytest.mark.asyncio
async def test_middleware_records_500(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(
            app=app,
            raise_app_exceptions=False,
        ),
        base_url='http://test',
    ) as client:
        response = await client.get('/api/v1/error')

    assert response.status_code == 500

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            {
                'method': 'GET',
                'route': '/api/v1/error',
                'status_code': '500',
            },
        )
        == 1
    )


@pytest.mark.asyncio
async def test_middleware_excludes_metrics_endpoint(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        response = await client.get('/api/v1/metrics')

    assert response.status_code == 200

    assert list(registry.collect())[0].samples == []


@pytest.mark.asyncio
async def test_middleware_records_422(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        response = await client.get('/api/v1/tickets/not-an-integer')

    assert response.status_code == 422

    labels = {
        'method': 'GET',
        'route': '/api/v1/tickets/{ticket_id}',
        'status_code': '422',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 1
    )


@pytest.mark.asyncio
async def test_middleware_records_405(registry):
    app = make_app(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        response = await client.post('/api/v1/tickets/123')

    assert response.status_code == 405

    labels = {
        'method': 'POST',
        'route': '/api/v1/tickets/{ticket_id}',
        'status_code': '405',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 1
    )
