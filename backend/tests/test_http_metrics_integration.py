from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from app.api.v1.metrics import get_ai_metrics
from app.api.v1.metrics import router as metrics_router
from app.core.ai_metrics import AIMetrics
from app.core.http_metrics import HTTPMetrics
from app.core.http_metrics_middleware import HTTPMetricsMiddleware
from app.core.settings import Settings, get_settings

TEST_TOKEN = 'test-http-integration-token'


def make_app():
    registry = CollectorRegistry()
    ai_metrics = AIMetrics(registry=registry)
    http_metrics = HTTPMetrics(registry=registry)

    app = FastAPI()

    app.add_middleware(
        HTTPMetricsMiddleware,
        metrics=http_metrics,
    )

    app.include_router(metrics_router, prefix='/api/v1')

    @app.get('/api/v1/test/{item_id}')
    async def get_item(item_id: int):
        return {'item_id': item_id}

    app.dependency_overrides[get_settings] = lambda: Settings(
        DATABASE_URL='sqlite+aiosqlite:///:memory:',
        JWT_SECRET_KEY='test-secret',
        METRICS_TOKEN=TEST_TOKEN,
    )
    app.dependency_overrides[get_ai_metrics] = lambda: ai_metrics

    return app, registry


def test_http_metrics_are_recorded():
    app, registry = make_app()

    with TestClient(app) as client:
        response = client.get('/api/v1/test/123')

    assert response.status_code == status.HTTP_200_OK

    labels = {
        'method': 'GET',
        'route': '/api/v1/test/{item_id}',
        'status_code': '200',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 1
    )


def test_metrics_endpoint_exports_http_and_ai():
    app, registry = make_app()

    with TestClient(app) as client:
        response = client.get('/api/v1/test/123')
        assert response.status_code == 200

        metrics_response = client.get(
            '/api/v1/metrics',
            headers={'X-Metrics-Token': TEST_TOKEN},
        )

    assert metrics_response.status_code == status.HTTP_200_OK

    body = metrics_response.text

    assert 'smartdesk_http_requests_total' in body
    assert 'smartdesk_http_request_duration_seconds' in body
    assert 'smartdesk_ai_classifications_total' in body

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            {
                'method': 'GET',
                'route': '/api/v1/test/{item_id}',
                'status_code': '200',
            },
        )
        == 1
    )


def test_metrics_endpoint_is_not_counted():
    app, registry = make_app()

    with TestClient(app) as client:
        response = client.get(
            '/api/v1/metrics',
            headers={'X-Metrics-Token': TEST_TOKEN},
        )

    assert response.status_code == status.HTTP_200_OK

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            {
                'method': 'GET',
                'route': '/api/v1/metrics',
                'status_code': '200',
            },
        )
        is None
    )
