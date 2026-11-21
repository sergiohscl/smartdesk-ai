import json
from collections import Counter

from evals.run_evaluation import DATASET_PATHS


def load_independent_dataset():
    path = DATASET_PATHS['independent']
    return json.loads(path.read_text(encoding='utf-8'))


def test_independent_dataset_has_20_cases():
    cases = load_independent_dataset()

    assert len(cases) == 20


def test_independent_dataset_has_unique_ids():
    cases = load_independent_dataset()

    ids = [case['id'] for case in cases]

    assert len(ids) == len(set(ids))
    assert all(
        case_id == f'AI-IND-{index:03d}'
        for index, case_id in enumerate(ids, start=1)
    )


def test_independent_dataset_has_required_fields():
    cases = load_independent_dataset()

    required = {
        'id',
        'title',
        'description',
        'expected_category',
        'expected_priority',
    }

    for case in cases:
        assert set(case) == required

        for value in case.values():
            assert isinstance(value, str)
            assert value.strip()


def test_independent_dataset_has_balanced_priorities():
    cases = load_independent_dataset()

    priorities = Counter(case['expected_priority'] for case in cases)

    assert priorities == {
        'low': 5,
        'medium': 5,
        'high': 5,
        'critical': 5,
    }


def test_independent_dataset_has_valid_categories():
    cases = load_independent_dataset()

    valid_categories = {
        'hardware',
        'software',
        'network',
        'access',
        'other',
    }

    categories = {case['expected_category'] for case in cases}

    assert categories == valid_categories


def test_independent_dataset_differs_from_golden():
    independent = load_independent_dataset()

    golden_path = DATASET_PATHS['golden']
    golden = json.loads(golden_path.read_text(encoding='utf-8'))

    independent_ids = {case['id'] for case in independent}
    golden_ids = {case['id'] for case in golden}

    assert independent_ids.isdisjoint(golden_ids)
