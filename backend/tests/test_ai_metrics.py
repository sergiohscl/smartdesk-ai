import pytest

from evals.metrics import EvaluationResult, calculate_metrics


def make_result(
    case_id: str,
    expected_category: str,
    predicted_category: str,
    expected_priority: str,
    predicted_priority: str,
) -> EvaluationResult:
    return EvaluationResult(
        case_id=case_id,
        expected_category=expected_category,
        predicted_category=predicted_category,
        expected_priority=expected_priority,
        predicted_priority=predicted_priority,
    )


def test_calculate_metrics_all_correct():
    results = [
        make_result('001', 'network', 'network', 'high', 'high'),
        make_result('002', 'software', 'software', 'low', 'low'),
    ]

    metrics = calculate_metrics(results)

    assert metrics.total == 2
    assert metrics.category_accuracy == 1.0
    assert metrics.priority_accuracy == 1.0
    assert metrics.full_accuracy == 1.0


def test_calculate_metrics_partial_errors():
    results = [
        make_result('001', 'network', 'network', 'high', 'medium'),
        make_result('002', 'software', 'hardware', 'low', 'low'),
        make_result('003', 'access', 'access', 'critical', 'critical'),
        make_result('004', 'other', 'other', 'low', 'low'),
    ]

    metrics = calculate_metrics(results)

    assert metrics.total == 4
    assert metrics.category_accuracy == 0.75
    assert metrics.priority_accuracy == 0.75
    assert metrics.full_accuracy == 0.5


def test_calculate_metrics_all_wrong():
    results = [
        make_result('001', 'network', 'software', 'high', 'low'),
    ]

    metrics = calculate_metrics(results)

    assert metrics.category_accuracy == 0.0
    assert metrics.priority_accuracy == 0.0
    assert metrics.full_accuracy == 0.0


def test_calculate_metrics_empty_results():
    with pytest.raises(
        ValueError,
        match='A avaliação precisa de resultados',
    ):
        calculate_metrics([])
