from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    expected_category: str
    predicted_category: str
    expected_priority: str
    predicted_priority: str
    predicted_reason: str | None = None

    @property
    def category_correct(self) -> bool:
        return self.expected_category == self.predicted_category

    @property
    def priority_correct(self) -> bool:
        return self.expected_priority == self.predicted_priority

    @property
    def fully_correct(self) -> bool:
        return self.category_correct and self.priority_correct


@dataclass(frozen=True)
class EvaluationMetrics:
    total: int
    category_accuracy: float
    priority_accuracy: float
    full_accuracy: float


def calculate_metrics(
    results: list[EvaluationResult],
) -> EvaluationMetrics:
    if not results:
        raise ValueError('A avaliação precisa de resultados.')

    total = len(results)

    category_hits = sum(result.category_correct for result in results)
    priority_hits = sum(result.priority_correct for result in results)
    full_hits = sum(result.fully_correct for result in results)

    return EvaluationMetrics(
        total=total,
        category_accuracy=category_hits / total,
        priority_accuracy=priority_hits / total,
        full_accuracy=full_hits / total,
    )
