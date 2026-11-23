import pytest
from prometheus_client import CollectorRegistry

from app.core.http_metrics import HTTPMetrics


@pytest.fixture
def registry():
    return CollectorRegistry()


def test_http_metrics_records_request(registry):
    metrics = HTTPMetrics(registry=registry)

    metrics.record_request(
        method='GET',
        route='/api/v1/tickets',
        status_code=200,
        duration_seconds=0.25,
    )

    labels = {
        'method': 'GET',
        'route': '/api/v1/tickets',
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

    assert registry.get_sample_value(
        'smartdesk_http_request_duration_seconds_sum',
        labels,
    ) == pytest.approx(0.25)


def test_http_metrics_accumulates_requests(registry):
    metrics = HTTPMetrics(registry=registry)

    for _ in range(3):
        metrics.record_request(
            method='GET',
            route='/api/v1/tickets',
            status_code=200,
            duration_seconds=0.2,
        )

    labels = {
        'method': 'GET',
        'route': '/api/v1/tickets',
        'status_code': '200',
    }

    assert (
        registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 3
    )

    assert registry.get_sample_value(
        'smartdesk_http_request_duration_seconds_sum',
        labels,
    ) == pytest.approx(0.6)


def test_http_metrics_separates_status_codes(registry):
    metrics = HTTPMetrics(registry=registry)

    metrics.record_request(
        method='GET',
        route='/api/v1/tickets',
        status_code=200,
        duration_seconds=0.1,
    )

    metrics.record_request(
        method='GET',
        route='/api/v1/tickets',
        status_code=404,
        duration_seconds=0.1,
    )

    for status_code in ('200', '404'):
        assert (
            registry.get_sample_value(
                'smartdesk_http_requests_total',
                {
                    'method': 'GET',
                    'route': '/api/v1/tickets',
                    'status_code': status_code,
                },
            )
            == 1
        )


def test_http_metrics_registries_are_isolated():
    first_registry = CollectorRegistry()
    second_registry = CollectorRegistry()

    first_metrics = HTTPMetrics(registry=first_registry)
    HTTPMetrics(registry=second_registry)

    first_metrics.record_request(
        method='POST',
        route='/api/v1/tickets',
        status_code=201,
        duration_seconds=0.3,
    )

    labels = {
        'method': 'POST',
        'route': '/api/v1/tickets',
        'status_code': '201',
    }

    assert (
        first_registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        == 1
    )

    assert (
        second_registry.get_sample_value(
            'smartdesk_http_requests_total',
            labels,
        )
        is None
    )
