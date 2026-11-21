from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict

from app.services.ai_service import AIService, AIServiceError
from evals.metrics import (
    EvaluationMetrics,
    EvaluationResult,
    calculate_metrics,
)


class EvaluationCase(TypedDict):
    id: str
    title: str
    description: str
    expected_category: str
    expected_priority: str


@dataclass(frozen=True)
class EvaluationFailure:
    case_id: str
    error_type: str


@dataclass(frozen=True)
class EvaluationReport:
    results: list[EvaluationResult]
    failures: list[EvaluationFailure]
    metrics: EvaluationMetrics | None
    total_cases: int
    success_rate: float


async def evaluate_cases(
    service: AIService,
    cases: Sequence[EvaluationCase],
) -> EvaluationReport:
    if not cases:
        raise ValueError('A avaliação precisa de chamados.')

    results: list[EvaluationResult] = []
    failures: list[EvaluationFailure] = []

    for case in cases:
        try:
            classification = await service.analyze_ticket(
                title=case['title'],
                description=case['description'],
            )
        except AIServiceError:
            failures.append(
                EvaluationFailure(
                    case_id=case['id'],
                    error_type='ai_service_error',
                )
            )
            continue

        results.append(
            EvaluationResult(
                case_id=case['id'],
                expected_category=case['expected_category'],
                predicted_category=classification.suggested_category.value,
                expected_priority=case['expected_priority'],
                predicted_priority=classification.suggested_priority.value,
                predicted_reason=classification.reason,
            )
        )

    metrics = calculate_metrics(results) if results else None

    return EvaluationReport(
        results=results,
        failures=failures,
        metrics=metrics,
        total_cases=len(cases),
        success_rate=len(results) / len(cases),
    )
