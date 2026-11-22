import pytest
from prometheus_client import CollectorRegistry

from app.core.ai_metrics import AIMetrics


@pytest.fixture
def registry():
    return CollectorRegistry()


def test_ai_metrics_success(registry):
    metrics = AIMetrics(registry=registry)

    metrics.record_classification(
        outcome='success',
        duration_seconds=0.25,
        model='test-model',
        prompt_version='v3',
    )

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

    assert registry.get_sample_value(
        'smartdesk_ai_classification_duration_seconds_sum',
        labels,
    ) == pytest.approx(0.25)


def test_ai_metrics_error(registry):
    metrics = AIMetrics(registry=registry)

    metrics.record_classification(
        outcome='error',
        duration_seconds=1.5,
        model='test-model',
        prompt_version='v3',
        error_category='timeout',
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
            'smartdesk_ai_errors_total',
            {
                'error_category': 'timeout',
                'model': 'test-model',
                'prompt_version': 'v3',
            },
        )
        == 1
    )


def test_ai_metrics_accumulates_classifications(registry):
    metrics = AIMetrics(registry=registry)

    for _ in range(3):
        metrics.record_classification(
            outcome='success',
            duration_seconds=0.2,
            model='test-model',
            prompt_version='v3',
        )

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
        == 3
    )

    assert (
        registry.get_sample_value(
            'smartdesk_ai_classification_duration_seconds_count',
            labels,
        )
        == 3
    )

    assert registry.get_sample_value(
        'smartdesk_ai_classification_duration_seconds_sum',
        labels,
    ) == pytest.approx(0.6)


def test_ai_metrics_registries_are_isolated():
    first_registry = CollectorRegistry()
    second_registry = CollectorRegistry()

    first_metrics = AIMetrics(registry=first_registry)
    second_metrics = AIMetrics(registry=second_registry)

    first_metrics.record_classification(
        outcome='success',
        duration_seconds=0.5,
        model='test-model',
        prompt_version='v3',
    )

    second_metrics.record_classification(
        outcome='success',
        duration_seconds=0.3,
        model='test-model',
        prompt_version='v3',
    )

    labels = {
        'outcome': 'success',
        'model': 'test-model',
        'prompt_version': 'v3',
    }

    assert (
        first_registry.get_sample_value(
            'smartdesk_ai_classifications_total',
            labels,
        )
        == 1
    )

    assert (
        second_registry.get_sample_value(
            'smartdesk_ai_classifications_total',
            labels,
        )
        == 1
    )

    assert first_registry.get_sample_value(
        'smartdesk_ai_classification_duration_seconds_sum',
        labels,
    ) == pytest.approx(0.5)

    assert second_registry.get_sample_value(
        'smartdesk_ai_classification_duration_seconds_sum',
        labels,
    ) == pytest.approx(0.3)
