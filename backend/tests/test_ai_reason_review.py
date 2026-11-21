import pytest
from pydantic import ValidationError

from evals.reason_review import (
    ReasonReview,
    ReasonReviewDocument,
    ReviewStatus,
    summarize_reviews,
)


def make_review(
    case_id: str = 'AI-IND-001',
    **overrides,
) -> ReasonReview:
    data = {
        'case_id': case_id,
        'coherence': ReviewStatus.PASS,
        'grounding': ReviewStatus.PASS,
        'faithfulness': ReviewStatus.PASS,
        'clarity': ReviewStatus.PASS,
    }
    data.update(overrides)
    return ReasonReview.model_validate(data)


def test_review_accepts_valid_statuses():
    review = make_review()

    assert review.case_id == 'AI-IND-001'
    assert review.coherence == ReviewStatus.PASS
    assert not review.notes


def test_review_rejects_invalid_status():
    with pytest.raises(ValidationError):
        make_review(coherence='invalid')


@pytest.mark.parametrize(
    'field',
    ['coherence', 'grounding', 'faithfulness', 'clarity'],
)
def test_review_requires_notes_for_fail(field):
    with pytest.raises(ValidationError):
        make_review(**{field: 'fail'})


@pytest.mark.parametrize(
    'field',
    ['coherence', 'grounding', 'faithfulness', 'clarity'],
)
def test_review_requires_notes_for_uncertain(field):
    with pytest.raises(ValidationError):
        make_review(**{field: 'uncertain'})


def test_review_accepts_fail_with_notes():
    review = make_review(
        clarity='fail',
        notes='Foram encontradas palavras unidas.',
    )

    assert review.clarity == ReviewStatus.FAIL


def test_review_rejects_extra_fields():
    with pytest.raises(ValidationError):
        make_review(unexpected_field=True)


def test_review_rejects_empty_case_id():
    with pytest.raises(ValidationError):
        make_review(case_id='')


def test_summary_counts_all_statuses():
    reviews = [
        make_review('AI-IND-001'),
        make_review(
            'AI-IND-002',
            clarity='fail',
            notes='Problemas de espaçamento.',
        ),
        make_review(
            'AI-IND-003',
            grounding='uncertain',
            notes='Requer análise adicional.',
        ),
    ]

    summary = summarize_reviews(reviews)

    assert summary.total_reviews == 3
    assert summary.coherence == {
        'pass': 3,
        'fail': 0,
        'uncertain': 0,
    }
    assert summary.grounding['uncertain'] == 1
    assert summary.clarity['fail'] == 1


def test_summary_rejects_duplicate_cases():
    reviews = [
        make_review('AI-IND-001'),
        make_review('AI-IND-001'),
    ]

    with pytest.raises(ValueError, match='duplicadas'):
        summarize_reviews(reviews)


def test_summary_rejects_empty_reviews():
    with pytest.raises(ValueError, match='Nenhuma avaliação'):
        summarize_reviews([])


def make_review_document(**overrides) -> ReasonReviewDocument:
    data = {
        'review_version': 'v1',
        'dataset_version': 'independent-v1',
        'dataset_sha256': 'a' * 64,
        'report_sha256': 'b' * 64,
        'reviews': [make_review()],
    }
    data.update(overrides)
    return ReasonReviewDocument.model_validate(data)


def test_review_document_accepts_valid_data():
    document = make_review_document()

    assert document.review_version == 'v1'
    assert document.dataset_version == 'independent-v1'
    assert len(document.reviews) == 1


def test_review_document_rejects_invalid_version():
    with pytest.raises(ValidationError):
        make_review_document(review_version='v2')


@pytest.mark.parametrize(
    'field',
    ['dataset_sha256', 'report_sha256'],
)
def test_review_document_rejects_invalid_hash(field):
    with pytest.raises(ValidationError):
        make_review_document(**{field: 'invalid-hash'})


def test_review_document_rejects_empty_reviews():
    with pytest.raises(ValidationError):
        make_review_document(reviews=[])


def test_review_document_rejects_duplicate_cases():
    reviews = [
        make_review('AI-IND-001'),
        make_review('AI-IND-001'),
    ]

    with pytest.raises(ValidationError, match='duplicadas'):
        make_review_document(reviews=reviews)


def test_review_document_rejects_extra_fields():
    with pytest.raises(ValidationError):
        make_review_document(unexpected_field=True)


def test_review_document_rejects_missing_dataset_version():
    with pytest.raises(ValidationError):
        make_review_document(dataset_version='')
