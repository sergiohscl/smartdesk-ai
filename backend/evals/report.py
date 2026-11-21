from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from evals.runner import EvaluationReport


def serialize_report(
    report: EvaluationReport,
    model: str,
    dataset_version: str,
    prompt_version: str,
) -> dict[str, Any]:
    return {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'model': model,
        'dataset_version': dataset_version,
        'prompt_version': prompt_version,
        'total_cases': report.total_cases,
        'successful_cases': len(report.results),
        'failed_cases': len(report.failures),
        'success_rate': report.success_rate,
        'metrics': (
            asdict(report.metrics) if report.metrics is not None else None
        ),
        'results': [
            {
                **asdict(result),
                'category_correct': result.category_correct,
                'priority_correct': result.priority_correct,
                'fully_correct': result.fully_correct,
            }
            for result in report.results
        ],
        'failures': [asdict(failure) for failure in report.failures],
    }
