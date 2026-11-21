import hashlib
from copy import deepcopy

import pytest

from evals.consolidate_reports import calculate_file_hash, consolidate

METADATA = {
    'model': 'gpt-6-luna',
    'dataset_name': 'independent',
    'dataset_version': 'independent-v1',
    'dataset_sha256': 'dataset-hash',
    'prompt_version': 'v3',
    'prompt_sha256': 'prompt-hash',
    'policy_sha256': 'policy-hash',
    'mode': 'real',
}


def make_result(
    case_id: str,
    expected_category: str = 'hardware',
    predicted_category: str = 'hardware',
    expected_priority: str = 'low',
    predicted_priority: str = 'low',
) -> dict:
    return {
        'case_id': case_id,
        'expected_category': expected_category,
        'predicted_category': predicted_category,
        'expected_priority': expected_priority,
        'predicted_priority': predicted_priority,
        'predicted_reason': 'Justificativa simulada.',
    }


def make_report(*results: dict) -> dict:
    return {
        **METADATA,
        'results': list(results),
        'failures': [],
    }


def test_consolidate_success():
    reports = [
        make_report(make_result('AI-IND-001')),
        make_report(
            make_result(
                'AI-IND-002',
                expected_category='software',
                predicted_category='software',
                expected_priority='medium',
                predicted_priority='medium',
            )
        ),
    ]

    consolidated = consolidate(
        reports,
        {'AI-IND-001', 'AI-IND-002'},
    )

    assert consolidated['total_cases'] == 2
    assert consolidated['successful_cases'] == 2
    assert consolidated['failed_cases'] == 0
    assert consolidated['success_rate'] == 1.0
    assert consolidated['metrics']['full_accuracy'] == 1.0


def test_consolidate_category_divergence():
    reports = [
        make_report(
            make_result(
                'AI-IND-001',
                expected_category='hardware',
                predicted_category='software',
            )
        )
    ]

    consolidated = consolidate(reports, {'AI-IND-001'})

    assert consolidated['metrics']['category_accuracy'] == 0.0
    assert consolidated['metrics']['priority_accuracy'] == 1.0
    assert consolidated['metrics']['full_accuracy'] == 0.0
    assert len(consolidated['divergences']) == 1
    assert consolidated['divergences'][0]['case_id'] == 'AI-IND-001'


def test_consolidate_priority_divergence():
    reports = [
        make_report(
            make_result(
                'AI-IND-001',
                expected_priority='high',
                predicted_priority='critical',
            )
        )
    ]

    consolidated = consolidate(reports, {'AI-IND-001'})

    assert consolidated['metrics']['category_accuracy'] == 1.0
    assert consolidated['metrics']['priority_accuracy'] == 0.0
    assert consolidated['metrics']['full_accuracy'] == 0.0


def test_consolidate_duplicate_ids():
    reports = [
        make_report(make_result('AI-IND-001')),
        make_report(make_result('AI-IND-001')),
    ]

    with pytest.raises(ValueError, match='ID duplicado'):
        consolidate(reports, {'AI-IND-001'})


def test_consolidate_missing_ids():
    reports = [
        make_report(make_result('AI-IND-001')),
    ]

    with pytest.raises(ValueError, match='IDs inválidos'):
        consolidate(
            reports,
            {'AI-IND-001', 'AI-IND-002'},
        )


def test_consolidate_unexpected_ids():
    reports = [
        make_report(make_result('AI-IND-999')),
    ]

    with pytest.raises(ValueError, match='IDs inválidos'):
        consolidate(reports, {'AI-IND-001'})


def test_consolidate_inconsistent_metadata():
    first = make_report(make_result('AI-IND-001'))
    second = deepcopy(make_report(make_result('AI-IND-002')))
    second['prompt_version'] = 'v4'

    with pytest.raises(
        ValueError,
        match='Metadado inconsistente',
    ):
        consolidate(
            [first, second],
            {'AI-IND-001', 'AI-IND-002'},
        )


def test_consolidate_missing_metadata():
    report = make_report(make_result('AI-IND-001'))
    del report['dataset_sha256']

    with pytest.raises(ValueError, match='Metadado ausente'):
        consolidate([report], {'AI-IND-001'})


def test_consolidate_rejects_mock_mode():
    report = make_report(make_result('AI-IND-001'))
    report['mode'] = 'mock'

    with pytest.raises(ValueError, match='relatórios reais'):
        consolidate([report], {'AI-IND-001'})


def test_consolidate_rejects_failures():
    report = make_report(make_result('AI-IND-001'))
    report['failures'] = [
        {
            'case_id': 'AI-IND-002',
            'error_type': 'ai_service_error',
        }
    ]

    with pytest.raises(
        ValueError,
        match='Relatório contém falha',
    ):
        consolidate(
            [report],
            {'AI-IND-001', 'AI-IND-002'},
        )


def test_consolidate_category_confusion_matrix():
    reports = [
        make_report(
            make_result(
                'AI-IND-001',
                expected_category='hardware',
                predicted_category='software',
            ),
            make_result(
                'AI-IND-002',
                expected_category='hardware',
                predicted_category='hardware',
            ),
        )
    ]

    consolidated = consolidate(
        reports,
        {'AI-IND-001', 'AI-IND-002'},
    )

    matrix = consolidated['category_confusion_matrix']

    assert matrix['hardware']['software'] == 1
    assert matrix['hardware']['hardware'] == 1


def test_consolidate_priority_confusion_matrix():
    reports = [
        make_report(
            make_result(
                'AI-IND-001',
                expected_priority='medium',
                predicted_priority='high',
            )
        )
    ]

    consolidated = consolidate(reports, {'AI-IND-001'})

    matrix = consolidated['priority_confusion_matrix']

    assert matrix['medium']['high'] == 1


def test_consolidate_metrics_by_priority():
    reports = [
        make_report(
            make_result('AI-IND-001'),
            make_result(
                'AI-IND-002',
                expected_category='software',
                predicted_category='hardware',
                expected_priority='medium',
                predicted_priority='medium',
            ),
        )
    ]

    consolidated = consolidate(
        reports,
        {'AI-IND-001', 'AI-IND-002'},
    )

    assert consolidated['metrics_by_priority']['low']['full_accuracy'] == 1.0
    assert (
        consolidated['metrics_by_priority']['medium']['full_accuracy'] == 0.0
    )


def test_consolidate_rejects_unknown_category():
    reports = [
        make_report(
            make_result(
                'AI-IND-001',
                predicted_category='unknown',
            )
        )
    ]

    with pytest.raises(ValueError, match='Classe desconhecida'):
        consolidate(reports, {'AI-IND-001'})


def test_consolidate_rejects_empty_reports():
    with pytest.raises(ValueError, match='Nenhum relatório'):
        consolidate([], {'AI-IND-001'})


def test_calculate_file_hash(tmp_path):
    dataset = tmp_path / 'dataset.json'
    dataset.write_text('{"test": true}', encoding='utf-8')

    expected = hashlib.sha256(dataset.read_bytes()).hexdigest()

    assert calculate_file_hash(dataset) == expected


def test_calculate_file_hash_detects_changes(tmp_path):
    dataset = tmp_path / 'dataset.json'
    dataset.write_text('versao-original', encoding='utf-8')

    original_hash = calculate_file_hash(dataset)

    dataset.write_text('versao-alterada', encoding='utf-8')

    modified_hash = calculate_file_hash(dataset)

    assert original_hash != modified_hash
