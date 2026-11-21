import hashlib
import json
import sys
from unittest.mock import patch

import pytest

from evals import run_evaluation
from evals.run_evaluation import (
    DATASET_PATHS,
    calculate_dataset_hash,
)


def test_load_cases_limit():
    cases = run_evaluation.load_cases(5)

    assert len(cases) == 5


@pytest.mark.parametrize('limit', [0, -1, 21])
def test_load_cases_invalid_limit(limit):
    with pytest.raises(
        ValueError,
        match='O limite deve estar entre 1 e 20',
    ):
        run_evaluation.load_cases(limit)


def test_parse_args_defaults(monkeypatch):
    monkeypatch.setattr(
        sys,
        'argv',
        ['run_evaluation'],
    )

    args = run_evaluation.parse_args()

    assert args.mode == 'mock'
    assert args.limit == 5
    assert args.confirm_api_cost is False


@pytest.mark.asyncio
async def test_real_mode_requires_confirmation(monkeypatch):
    monkeypatch.setattr(
        sys,
        'argv',
        ['run_evaluation', '--mode', 'real'],
    )

    with pytest.raises(
        SystemExit,
        match='Modo real exige --confirm-api-cost',
    ):
        await run_evaluation.run()


@pytest.mark.asyncio
async def test_mock_mode_does_not_call_openai(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'run_evaluation',
            '--mode',
            'mock',
            '--limit',
            '1',
        ],
    )

    monkeypatch.setattr(
        run_evaluation,
        'REPORTS_DIR',
        tmp_path,
    )

    with patch.object(
        run_evaluation,
        'AsyncOpenAI',
    ) as mock_openai:
        await run_evaluation.run()

    mock_openai.assert_not_called()

    reports = list(tmp_path.glob('evaluation_mock_*.json'))

    assert len(reports) == 1

    data = json.loads(reports[0].read_text(encoding='utf-8'))

    assert data['mode'] == 'mock'
    assert data['total_cases'] == 1
    assert data['successful_cases'] == 1
    assert data['dataset_sha256'] == (run_evaluation.calculate_dataset_hash())
    assert data['prompt_sha256'] == (run_evaluation.calculate_prompt_hash())
    assert data['policy_sha256'] == (run_evaluation.calculate_policy_hash())


def test_dataset_hash_is_sha256():
    dataset_hash = run_evaluation.calculate_dataset_hash()

    assert len(dataset_hash) == 64
    assert all(char in '0123456789abcdef' for char in dataset_hash)


def test_dataset_hash_changes_with_content(
    monkeypatch,
    tmp_path,
):
    dataset = tmp_path / 'dataset.json'
    dataset.write_text('[]', encoding='utf-8')

    monkeypatch.setitem(
        run_evaluation.DATASET_PATHS,
        'golden',
        dataset,
    )

    original_hash = run_evaluation.calculate_dataset_hash()

    dataset.write_text('[{}]', encoding='utf-8')

    updated_hash = run_evaluation.calculate_dataset_hash()

    assert original_hash != updated_hash


def test_prompt_hash_is_sha256():
    prompt_hash = run_evaluation.calculate_prompt_hash()

    assert len(prompt_hash) == 64
    assert all(char in '0123456789abcdef' for char in prompt_hash)


def test_prompt_hash_changes_with_instructions(monkeypatch):
    original_hash = run_evaluation.calculate_prompt_hash()

    monkeypatch.setattr(
        run_evaluation,
        'CLASSIFICATION_INSTRUCTIONS',
        'Instruções modificadas para teste.',
    )

    updated_hash = run_evaluation.calculate_prompt_hash()

    assert original_hash != updated_hash


def test_policy_hash_is_sha256():
    policy_hash = run_evaluation.calculate_policy_hash()

    assert len(policy_hash) == 64
    assert all(char in '0123456789abcdef' for char in policy_hash)


def test_policy_hash_changes_with_content(
    monkeypatch,
    tmp_path,
):
    policy = tmp_path / 'classification_policy.md'
    policy.write_text('# Política original', encoding='utf-8')

    monkeypatch.setattr(
        run_evaluation,
        'POLICY_PATH',
        policy,
    )

    original_hash = run_evaluation.calculate_policy_hash()

    policy.write_text(
        '# Política modificada',
        encoding='utf-8',
    )

    updated_hash = run_evaluation.calculate_policy_hash()

    assert original_hash != updated_hash


def test_load_cases_with_start():
    cases = run_evaluation.load_cases(limit=15, start=6)

    assert len(cases) == 15
    assert cases[0]['id'] == 'AI-EVAL-006'
    assert cases[-1]['id'] == 'AI-EVAL-020'


@pytest.mark.parametrize('start', [0, -1, 21])
def test_load_cases_invalid_start(start):
    with pytest.raises(
        ValueError,
        match='O início deve estar entre 1 e 20',
    ):
        run_evaluation.load_cases(limit=1, start=start)


def test_load_cases_interval_exceeds_dataset():
    with pytest.raises(
        ValueError,
        match='O intervalo solicitado excede os 20 casos',
    ):
        run_evaluation.load_cases(limit=5, start=18)


def test_dataset_hash_defaults_to_golden():
    expected = hashlib.sha256(DATASET_PATHS['golden'].read_bytes()).hexdigest()

    assert calculate_dataset_hash() == expected


def test_dataset_hash_uses_selected_file(tmp_path, monkeypatch):
    dataset_path = tmp_path / 'independent.json'
    dataset_path.write_text('[]', encoding='utf-8')

    monkeypatch.setitem(
        DATASET_PATHS,
        'independent',
        dataset_path,
    )

    expected = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    assert calculate_dataset_hash('independent') == expected


def test_dataset_hash_rejects_unknown_dataset():
    with pytest.raises(ValueError, match='Dataset inválido'):
        calculate_dataset_hash('unknown')


def test_load_cases_uses_independent_dataset(
    monkeypatch,
    tmp_path,
):
    dataset = tmp_path / 'independent.json'

    cases = [
        {
            'id': 'AI-IND-001',
            'title': 'Chamado independente',
            'description': 'Descrição de teste.',
            'expected_category': 'software',
            'expected_priority': 'medium',
        },
        {
            'id': 'AI-IND-002',
            'title': 'Segundo chamado',
            'description': 'Outra descrição.',
            'expected_category': 'hardware',
            'expected_priority': 'low',
        },
    ]

    dataset.write_text(
        json.dumps(cases),
        encoding='utf-8',
    )

    monkeypatch.setitem(
        run_evaluation.DATASET_PATHS,
        'independent',
        dataset,
    )

    result = run_evaluation.load_cases(
        limit=2,
        dataset='independent',
    )

    assert len(result) == 2
    assert result[0]['id'] == 'AI-IND-001'
    assert result[1]['id'] == 'AI-IND-002'


def test_load_cases_rejects_unknown_dataset():
    with pytest.raises(ValueError, match='Dataset inválido'):
        run_evaluation.load_cases(
            limit=1,
            dataset='unknown',
        )


def test_load_cases_rejects_missing_dataset(
    monkeypatch,
    tmp_path,
):
    missing_path = tmp_path / 'missing.json'

    monkeypatch.setitem(
        run_evaluation.DATASET_PATHS,
        'independent',
        missing_path,
    )

    with pytest.raises(
        FileNotFoundError,
        match='Dataset não encontrado',
    ):
        run_evaluation.load_cases(
            limit=1,
            dataset='independent',
        )


def test_load_cases_uses_dynamic_dataset_size(
    monkeypatch,
    tmp_path,
):
    dataset = tmp_path / 'small.json'

    cases = [
        {
            'id': f'AI-IND-{number:03d}',
            'title': f'Chamado {number}',
            'description': 'Descrição.',
            'expected_category': 'other',
            'expected_priority': 'low',
        }
        for number in range(1, 4)
    ]

    dataset.write_text(
        json.dumps(cases),
        encoding='utf-8',
    )

    monkeypatch.setitem(
        run_evaluation.DATASET_PATHS,
        'independent',
        dataset,
    )

    result = run_evaluation.load_cases(
        limit=2,
        start=2,
        dataset='independent',
    )

    assert [case['id'] for case in result] == [
        'AI-IND-002',
        'AI-IND-003',
    ]

    with pytest.raises(ValueError, match='limite'):
        run_evaluation.load_cases(
            limit=4,
            dataset='independent',
        )


def test_golden_and_independent_have_different_hashes():
    golden_hash = run_evaluation.calculate_dataset_hash('golden')
    independent_hash = run_evaluation.calculate_dataset_hash('independent')

    assert golden_hash != independent_hash
    assert len(golden_hash) == 64
    assert len(independent_hash) == 64


def test_independent_dataset_hash_matches_file():
    dataset_path = run_evaluation.DATASET_PATHS['independent']

    expected_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    actual_hash = run_evaluation.calculate_dataset_hash('independent')

    assert actual_hash == expected_hash


def test_independent_dataset_can_load_all_cases():
    cases = run_evaluation.load_cases(
        limit=20,
        dataset='independent',
    )

    assert len(cases) == 20
    assert cases[0]['id'] == 'AI-IND-001'
    assert cases[-1]['id'] == 'AI-IND-020'
