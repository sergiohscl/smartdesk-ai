import json

from evals.metrics import EvaluationMetrics, EvaluationResult
from evals.report import serialize_report
from evals.runner import EvaluationFailure, EvaluationReport


def test_serialize_report_success():
    result = EvaluationResult(
        case_id='AI-EVAL-001',
        expected_category='network',
        predicted_category='network',
        expected_priority='high',
        predicted_priority='high',
        predicted_reason='Rede indisponível para o setor.',
    )

    report = EvaluationReport(
        results=[result],
        failures=[],
        metrics=EvaluationMetrics(
            total=1,
            category_accuracy=1.0,
            priority_accuracy=1.0,
            full_accuracy=1.0,
        ),
        total_cases=1,
        success_rate=1.0,
    )

    data = serialize_report(
        report,
        model='test-model',
        dataset_version='v1',
        prompt_version='v1',
    )

    assert data['model'] == 'test-model'
    assert data['total_cases'] == 1
    assert data['successful_cases'] == 1
    assert data['failed_cases'] == 0
    assert data['metrics']['full_accuracy'] == 1.0
    assert data['results'][0]['fully_correct'] is True
    assert (
        data['results'][0]['predicted_reason']
        == 'Rede indisponível para o setor.'
    )
    assert data['prompt_version'] == 'v1'

    json.dumps(data)


def test_serialize_report_all_fail():
    report = EvaluationReport(
        results=[],
        failures=[
            EvaluationFailure(
                case_id='AI-EVAL-001',
                error_type='ai_service_error',
            )
        ],
        metrics=None,
        total_cases=1,
        success_rate=0.0,
    )

    data = serialize_report(
        report,
        model='test-model',
        dataset_version='v1',
        prompt_version='v1',
    )

    assert data['successful_cases'] == 0
    assert data['failed_cases'] == 1
    assert data['success_rate'] == 0.0
    assert data['metrics'] is None
    assert data['failures'][0]['case_id'] == 'AI-EVAL-001'

    json.dumps(data)
