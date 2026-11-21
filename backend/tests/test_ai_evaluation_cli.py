import asyncio
import hashlib
import json
from argparse import Namespace

import pytest

from evals import run_evaluation


@pytest.mark.parametrize(
    ('dataset_name', 'dataset_version'),
    [
        ('golden', 'golden-v1'),
        ('independent', 'independent-v1'),
    ],
)
def test_cli_generates_correct_dataset_report(
    monkeypatch,
    tmp_path,
    dataset_name,
    dataset_version,
):
    reports_dir = tmp_path / 'reports'

    monkeypatch.setattr(
        run_evaluation,
        'REPORTS_DIR',
        reports_dir,
    )

    args = Namespace(
        mode='mock',
        dataset=dataset_name,
        limit=2,
        start=1,
        confirm_api_cost=False,
    )

    monkeypatch.setattr(
        run_evaluation,
        'parse_args',
        lambda: args,
    )

    asyncio.run(run_evaluation.run())

    reports = list(reports_dir.glob('evaluation_mock_*.json'))

    assert len(reports) == 1

    report = json.loads(reports[0].read_text(encoding='utf-8'))

    dataset_path = run_evaluation.DATASET_PATHS[dataset_name]

    expected_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    assert report['mode'] == 'mock'
    assert report['dataset_name'] == dataset_name
    assert report['dataset_version'] == dataset_version
    assert report['dataset_sha256'] == expected_hash
    assert report['prompt_version'] == 'v3'
    assert report['total_cases'] == 2

    assert len(report['results']) == 2

    assert all(
        result['predicted_reason'] == 'Resposta simulada.'
        for result in report['results']
    )
