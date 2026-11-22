from fastapi import status
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from app.api.v1.metrics import get_ai_metrics
from app.core.ai_metrics import AIMetrics
from app.core.settings import Settings, get_settings
from app.main import app

client = TestClient(app)

TEST_TOKEN = 'test-metrics-secret'


def make_settings(metrics_token: str | None) -> Settings:
    return Settings(
        DATABASE_URL='sqlite+aiosqlite:///:memory:',
        JWT_SECRET_KEY='test-secret',
        METRICS_TOKEN=metrics_token,
    )


def test_metrics_endpoint_without_token():
    app.dependency_overrides[get_settings] = lambda: make_settings(TEST_TOKEN)

    try:
        response = client.get('api/v1/metrics')

        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_metrics_endpoint_invalid_token():
    app.dependency_overrides[get_settings] = lambda: make_settings(TEST_TOKEN)

    try:
        response = client.get(
            'api/v1/metrics',
            headers={'X-Metrics-Token': 'invalid-token'},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_metrics_endpoint_without_configuration():
    app.dependency_overrides[get_settings] = lambda: make_settings(None)

    try:
        response = client.get(
            'api/v1/metrics',
            headers={'X-Metrics-Token': TEST_TOKEN},
        )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_metrics_endpoint_success():
    registry = CollectorRegistry()
    metrics = AIMetrics(registry=registry)

    metrics.record_classification(
        outcome='success',
        duration_seconds=0.25,
        model='test-model',
        prompt_version='v3',
    )

    app.dependency_overrides[get_settings] = lambda: make_settings(TEST_TOKEN)

    app.dependency_overrides[get_ai_metrics] = lambda: metrics

    try:
        response = client.get(
            'api/v1/metrics',
            headers={'X-Metrics-Token': TEST_TOKEN},
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'text/plain' in response.headers['content-type']
        assert (
            'smartdesk_ai_classifications_total'
            '{model="test-model",outcome="success",prompt_version="v3"} 1.0'
            in response.text
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_ai_metrics, None)


def test_metrics_endpoint_does_not_expose_token():
    app.dependency_overrides[get_settings] = lambda: make_settings(TEST_TOKEN)

    try:
        response = client.get(
            'api/v1/metrics',
            headers={'X-Metrics-Token': 'invalid-token'},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert TEST_TOKEN not in response.text
        assert 'invalid-token' not in response.text
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_metrics_endpoint_does_not_expose_metrics_without_auth():
    app.dependency_overrides[get_settings] = lambda: make_settings(TEST_TOKEN)

    try:
        response = client.get('api/v1/metrics')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'smartdesk_ai_classifications_total' not in response.text
        assert 'smartdesk_ai_errors_total' not in response.text
    finally:
        app.dependency_overrides.pop(get_settings, None)
