import json
from collections import Counter
from pathlib import Path

import pytest

from app.models.ticket import TicketPriority
from app.schemas.ai import AITicketCategory

DATASET_PATH = (
    Path(__file__).resolve().parents[1] / 'evals' / 'golden_dataset.json'
)


@pytest.fixture(scope='module')
def golden_dataset():
    return json.loads(DATASET_PATH.read_text(encoding='utf-8'))


def test_golden_dataset_has_20_cases(golden_dataset):
    assert len(golden_dataset) == 20


def test_golden_dataset_has_unique_ids(golden_dataset):
    ids = [case['id'] for case in golden_dataset]

    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    'field',
    ['id', 'title', 'description', 'expected_category', 'expected_priority'],
)
def test_golden_dataset_required_fields(golden_dataset, field):
    for case in golden_dataset:
        assert field in case
        assert isinstance(case[field], str)
        assert case[field].strip()


def test_golden_dataset_valid_categories(golden_dataset):
    valid_categories = {category.value for category in AITicketCategory}

    for case in golden_dataset:
        assert case['expected_category'] in valid_categories


def test_golden_dataset_valid_priorities(golden_dataset):
    valid_priorities = {priority.value for priority in TicketPriority}

    for case in golden_dataset:
        assert case['expected_priority'] in valid_priorities


def test_golden_dataset_input_limits(golden_dataset):
    for case in golden_dataset:
        assert len(case['title']) <= 200
        assert len(case['description']) <= 4000


def test_golden_dataset_category_distribution(golden_dataset):
    distribution = Counter(
        case['expected_category'] for case in golden_dataset
    )

    assert set(distribution) == {
        category.value for category in AITicketCategory
    }

    assert all(count == 4 for count in distribution.values())
