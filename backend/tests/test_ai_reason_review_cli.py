import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.reason_review import ReasonReviewDocument, ReviewStatus
from evals.reason_review_cli import (
    build_review_summary,
    calculate_sha256,
    load_review_document,
    validate_review_document,
)


@pytest.fixture
def review_files(tmp_path: Path):
    dataset_path = tmp_path / 'dataset.json'
    report_path = tmp_path / 'report.json'

    dataset = [
        {'id': 'AI-IND-001'},
        {'id': 'AI-IND-002'},
    ]

    dataset_path.write_text(
        json.dumps(dataset),
        encoding='utf-8',
    )

    report = {
        'dataset_version': 'independent-v1',
        'dataset_sha256': calculate_sha256(dataset_path),
        'results': [
            {'case_id': 'AI-IND-001'},
            {'case_id': 'AI-IND-002'},
        ],
    }

    report_path.write_text(
        json.dumps(report),
        encoding='utf-8',
    )

    return dataset_path, report_path


def make_document(
    dataset_path: Path,
    report_path: Path,
    case_ids: list[str] | None = None,
    **overrides,
) -> ReasonReviewDocument:
    if case_ids is None:
        case_ids = ['AI-IND-001']

    data = {
        'review_version': 'v1',
        'dataset_version': 'independent-v1',
        'dataset_sha256': calculate_sha256(dataset_path),
        'report_sha256': calculate_sha256(report_path),
        'reviews': [
            {
                'case_id': case_id,
                'coherence': 'pass',
                'grounding': 'pass',
                'faithfulness': 'pass',
                'clarity': 'pass',
            }
            for case_id in case_ids
        ],
    }

    data.update(overrides)
    return ReasonReviewDocument.model_validate(data)


def test_validate_review_document_success(review_files):
    dataset_path, report_path = review_files
    document = make_document(dataset_path, report_path)

    validate_review_document(
        document,
        dataset_path,
        report_path,
    )


def test_validate_review_document_partial_reviews(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        case_ids=['AI-IND-002'],
    )

    validate_review_document(
        document,
        dataset_path,
        report_path,
    )


def test_validate_review_document_invalid_dataset_hash(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        dataset_sha256='a' * 64,
    )

    with pytest.raises(ValueError, match='Hash do dataset'):
        validate_review_document(document, dataset_path, report_path)


def test_validate_review_document_invalid_report_hash(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        report_sha256='b' * 64,
    )

    with pytest.raises(ValueError, match='Hash do relatório'):
        validate_review_document(document, dataset_path, report_path)


def test_validate_review_document_invalid_version(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        dataset_version='another-version',
    )

    with pytest.raises(ValueError, match='Versão do dataset'):
        validate_review_document(document, dataset_path, report_path)


def test_validate_review_document_unknown_case(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        case_ids=['AI-IND-999'],
    )

    with pytest.raises(ValueError, match='identificadores inexistentes'):
        validate_review_document(document, dataset_path, report_path)


def test_validate_review_document_duplicate_dataset_ids(review_files):
    dataset_path, report_path = review_files

    dataset = [
        {'id': 'AI-IND-001'},
        {'id': 'AI-IND-001'},
    ]

    dataset_path.write_text(
        json.dumps(dataset),
        encoding='utf-8',
    )

    report = json.loads(report_path.read_text(encoding='utf-8'))

    report['dataset_sha256'] = calculate_sha256(dataset_path)

    report_path.write_text(
        json.dumps(report),
        encoding='utf-8',
    )

    document = make_document(dataset_path, report_path)

    with pytest.raises(
        ValueError,
        match='Dataset contém IDs duplicados',
    ):
        validate_review_document(
            document,
            dataset_path,
            report_path,
        )


def test_validate_review_document_duplicate_report_ids(review_files):
    dataset_path, report_path = review_files
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report['results'] = [
        {'case_id': 'AI-IND-001'},
        {'case_id': 'AI-IND-001'},
    ]
    report_path.write_text(json.dumps(report), encoding='utf-8')

    document = make_document(dataset_path, report_path)

    with pytest.raises(ValueError, match='Relatório contém IDs duplicados'):
        validate_review_document(document, dataset_path, report_path)


def test_validate_review_document_mismatched_case_ids(review_files):
    dataset_path, report_path = review_files
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report['results'][1]['case_id'] = 'AI-IND-999'
    report_path.write_text(json.dumps(report), encoding='utf-8')

    document = make_document(dataset_path, report_path)

    with pytest.raises(ValueError, match='casos diferentes'):
        validate_review_document(document, dataset_path, report_path)


def test_validate_review_document_report_dataset_hash_mismatch(review_files):
    dataset_path, report_path = review_files
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report['dataset_sha256'] = 'c' * 64
    report_path.write_text(json.dumps(report), encoding='utf-8')

    document = make_document(dataset_path, report_path)

    with pytest.raises(ValueError, match='Relatório não corresponde'):
        validate_review_document(document, dataset_path, report_path)


def test_load_review_document_success(review_files, tmp_path):
    dataset_path, report_path = review_files
    document = make_document(dataset_path, report_path)

    review_path = tmp_path / 'reviews.json'
    review_path.write_text(
        document.model_dump_json(),
        encoding='utf-8',
    )

    loaded = load_review_document(review_path)

    assert loaded == document


def test_load_review_document_invalid_json(tmp_path):
    review_path = tmp_path / 'reviews.json'
    review_path.write_text(
        '{invalid json',
        encoding='utf-8',
    )

    with pytest.raises(json.JSONDecodeError):
        load_review_document(review_path)


def test_load_review_document_invalid_schema(tmp_path):
    review_path = tmp_path / 'reviews.json'
    review_path.write_text(
        json.dumps({'review_version': 'v2'}),
        encoding='utf-8',
    )

    with pytest.raises(ValidationError):
        load_review_document(review_path)


def test_build_review_summary_success(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        case_ids=['AI-IND-001', 'AI-IND-002'],
    )

    summary = build_review_summary(
        document,
        dataset_path,
        report_path,
    )

    assert summary.total_reviews == 2
    assert summary.coherence['pass'] == 2
    assert summary.grounding['pass'] == 2
    assert summary.faithfulness['pass'] == 2
    assert summary.clarity['pass'] == 2


def test_build_review_summary_mixed_statuses(review_files):
    dataset_path, report_path = review_files

    document = make_document(
        dataset_path,
        report_path,
        case_ids=['AI-IND-001', 'AI-IND-002'],
    )

    document.reviews[1].coherence = ReviewStatus.FAIL
    document.reviews[1].notes = 'Justificativa incoerente.'

    summary = build_review_summary(
        document,
        dataset_path,
        report_path,
    )

    assert summary.coherence['pass'] == 1
    assert summary.coherence['fail'] == 1
    assert summary.coherence['uncertain'] == 0


def test_build_review_summary_rejects_invalid_hash(review_files):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        dataset_sha256='a' * 64,
    )

    with pytest.raises(ValueError, match='Hash do dataset'):
        build_review_summary(
            document,
            dataset_path,
            report_path,
        )


def test_cli_success(review_files, tmp_path):
    dataset_path, report_path = review_files
    document = make_document(
        dataset_path,
        report_path,
        case_ids=['AI-IND-001', 'AI-IND-002'],
    )

    review_path = tmp_path / 'reviews.json'
    review_path.write_text(
        document.model_dump_json(),
        encoding='utf-8',
    )

    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'evals.reason_review_cli',
            '--dataset',
            str(dataset_path),
            '--report',
            str(report_path),
            '--reviews',
            str(review_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    summary = json.loads(result.stdout)

    assert summary['total_reviews'] == 2
    assert summary['coherence']['pass'] == 2
    assert summary['grounding']['pass'] == 2
    assert summary['faithfulness']['pass'] == 2
    assert summary['clarity']['pass'] == 2


def test_cli_rejects_invalid_dataset_hash(review_files, tmp_path):
    dataset_path, report_path = review_files

    document = make_document(
        dataset_path,
        report_path,
        dataset_sha256='a' * 64,
    )

    review_path = tmp_path / 'reviews.json'
    review_path.write_text(
        document.model_dump_json(),
        encoding='utf-8',
    )

    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'evals.reason_review_cli',
            '--dataset',
            str(dataset_path),
            '--report',
            str(report_path),
            '--reviews',
            str(review_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert 'Hash do dataset' in result.stderr
