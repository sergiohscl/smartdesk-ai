from collections import Counter
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewStatus(StrEnum):
    PASS = 'pass'
    FAIL = 'fail'
    UNCERTAIN = 'uncertain'


class ReasonReview(BaseModel):
    model_config = ConfigDict(extra='forbid')

    case_id: str = Field(min_length=1)
    coherence: ReviewStatus
    grounding: ReviewStatus
    faithfulness: ReviewStatus
    clarity: ReviewStatus
    notes: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def validate_notes(self):
        statuses = (
            self.coherence,
            self.grounding,
            self.faithfulness,
            self.clarity,
        )

        if (
            ReviewStatus.FAIL in statuses or ReviewStatus.UNCERTAIN in statuses
        ) and not self.notes.strip():
            raise ValueError(
                'Avaliações fail ou uncertain exigem observações.'
            )

        return self


class ReviewSummary(BaseModel):
    total_reviews: int
    coherence: dict[str, int]
    grounding: dict[str, int]
    faithfulness: dict[str, int]
    clarity: dict[str, int]


def summarize_reviews(
    reviews: list[ReasonReview],
) -> ReviewSummary:
    if not reviews:
        raise ValueError('Nenhuma avaliação informada.')

    case_ids = [review.case_id for review in reviews]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError('Existem avaliações duplicadas.')

    def count_statuses(field: str) -> dict[str, int]:
        counts = Counter(getattr(review, field).value for review in reviews)

        return {
            status.value: counts.get(status.value, 0)
            for status in ReviewStatus
        }

    return ReviewSummary(
        total_reviews=len(reviews),
        coherence=count_statuses('coherence'),
        grounding=count_statuses('grounding'),
        faithfulness=count_statuses('faithfulness'),
        clarity=count_statuses('clarity'),
    )


class ReasonReviewDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')

    review_version: str = Field(pattern=r'^v1$')
    dataset_version: str = Field(min_length=1)
    dataset_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    report_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    reviews: list[ReasonReview] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_unique_cases(self) -> Self:
        case_ids = [review.case_id for review in self.reviews]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError('Existem avaliações duplicadas.')

        return self
