import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.metrics import EvaluationResult, calculate_metrics

METADATA_FIELDS = (
    'model',
    'dataset_name',
    'dataset_version',
    'dataset_sha256',
    'prompt_version',
    'prompt_sha256',
    'policy_sha256',
    'mode',
)

PRIORITIES = ('low', 'medium', 'high', 'critical')
CATEGORIES = ('hardware', 'software', 'network', 'access', 'other')


def load_reports(paths: list[Path]) -> list[dict[str, Any]]:
    if not paths:
        raise ValueError('Informe pelo menos um relatório.')

    reports = []

    for path in paths:
        with path.open(encoding='utf-8') as file:
            reports.append(json.load(file))

    return reports


def calculate_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_metadata(reports: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = {}

    for field in METADATA_FIELDS:
        values = [report.get(field) for report in reports]

        if any(value is None for value in values):
            raise ValueError(f'Metadado ausente: {field}')

        if len(set(values)) != 1:
            raise ValueError(f'Metadado inconsistente: {field}')

        metadata[field] = values[0]

    if metadata['mode'] != 'real':
        raise ValueError('A consolidação exige relatórios reais.')

    return metadata


def collect_results(
    reports: list[dict[str, Any]],
) -> list[EvaluationResult]:
    results = []
    seen_ids = set()

    for report in reports:
        for item in report['results']:
            case_id = item['case_id']

            if case_id in seen_ids:
                raise ValueError(f'ID duplicado: {case_id}')

            seen_ids.add(case_id)

            results.append(
                EvaluationResult(
                    case_id=case_id,
                    expected_category=item['expected_category'],
                    predicted_category=item['predicted_category'],
                    expected_priority=item['expected_priority'],
                    predicted_priority=item['predicted_priority'],
                    predicted_reason=item.get('predicted_reason'),
                )
            )

        for failure in report['failures']:
            raise ValueError(
                f'Relatório contém falha de avaliação: {failure["case_id"]}'
            )

    return sorted(results, key=lambda result: result.case_id)


def validate_case_ids(
    results: list[EvaluationResult],
    expected_ids: set[str],
) -> None:
    actual_ids = {result.case_id for result in results}

    missing = expected_ids - actual_ids
    unexpected = actual_ids - expected_ids

    if missing or unexpected:
        raise ValueError(
            f'IDs inválidos. '
            f'Ausentes: {sorted(missing)}. '
            f'Inesperados: {sorted(unexpected)}.'
        )


def confusion_matrix(
    results: list[EvaluationResult],
    labels: tuple[str, ...],
    expected_field: str,
    predicted_field: str,
) -> dict[str, dict[str, int]]:
    matrix = {
        expected: {predicted: 0 for predicted in labels} for expected in labels
    }

    for result in results:
        expected = getattr(result, expected_field)
        predicted = getattr(result, predicted_field)

        if expected not in labels or predicted not in labels:
            raise ValueError(f'Classe desconhecida: {expected} → {predicted}')

        matrix[expected][predicted] += 1

    return matrix


def metrics_by_priority(
    results: list[EvaluationResult],
) -> dict[str, dict[str, Any]]:
    output = {}

    for priority in PRIORITIES:
        subset = [
            result
            for result in results
            if result.expected_priority == priority
        ]

        if subset:
            output[priority] = asdict(calculate_metrics(subset))

    return output


def consolidate(
    reports: list[dict[str, Any]],
    expected_ids: set[str],
) -> dict[str, Any]:
    if not reports:
        raise ValueError('Nenhum relatório informado.')

    metadata = validate_metadata(reports)
    results = collect_results(reports)
    validate_case_ids(results, expected_ids)

    if not results:
        raise ValueError('Nenhum resultado encontrado.')

    metrics = calculate_metrics(results)

    divergences = [
        {
            **asdict(result),
            'category_correct': result.category_correct,
            'priority_correct': result.priority_correct,
        }
        for result in results
        if not result.fully_correct
    ]

    return {
        'created_at': datetime.now(timezone.utc).isoformat(),
        **metadata,
        'total_cases': len(results),
        'successful_cases': len(results),
        'failed_cases': 0,
        'success_rate': 1.0,
        'metrics': asdict(metrics),
        'metrics_by_priority': metrics_by_priority(results),
        'category_confusion_matrix': confusion_matrix(
            results,
            CATEGORIES,
            'expected_category',
            'predicted_category',
        ),
        'priority_confusion_matrix': confusion_matrix(
            results,
            PRIORITIES,
            'expected_priority',
            'predicted_priority',
        ),
        'category_distribution': dict(
            Counter(result.expected_category for result in results)
        ),
        'priority_distribution': dict(
            Counter(result.expected_priority for result in results)
        ),
        'divergences': divergences,
        'results': [
            {
                **asdict(result),
                'category_correct': result.category_correct,
                'priority_correct': result.priority_correct,
                'fully_correct': result.fully_correct,
            }
            for result in results
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Consolida avaliações reais da IA.'
    )

    parser.add_argument(
        'reports',
        nargs='+',
        type=Path,
        help='Arquivos JSON das avaliações.',
    )

    parser.add_argument(
        '--dataset',
        type=Path,
        default=Path('evals/independent_dataset_v1.json'),
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('evals/reports/independent_consolidated_v1.json'),
    )

    args = parser.parse_args()

    reports = load_reports(args.reports)

    with args.dataset.open(encoding='utf-8') as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError('Dataset deve conter uma lista de casos.')

    expected_ids = {case['id'] for case in dataset}

    if len(expected_ids) != len(dataset):
        raise ValueError('Dataset contém IDs duplicados.')

    consolidated = consolidate(reports, expected_ids)

    actual_dataset_hash = calculate_file_hash(args.dataset)
    expected_dataset_hash = consolidated['dataset_sha256']

    if actual_dataset_hash != expected_dataset_hash:
        raise ValueError(
            'Hash do dataset não corresponde ao utilizado '
            'nas avaliações reais.'
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(consolidated, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    print(f'Relatório consolidado: {args.output}')
    print(f'Casos: {consolidated["total_cases"]}')

    metrics = consolidated['metrics']

    print(f'Acurácia categoria: {metrics["category_accuracy"]:.2%}')
    print(f'Acurácia prioridade: {metrics["priority_accuracy"]:.2%}')
    print(f'Acurácia completa: {metrics["full_accuracy"]:.2%}')
    print(f'Divergências: {len(consolidated["divergences"])}')


if __name__ == '__main__':
    main()
