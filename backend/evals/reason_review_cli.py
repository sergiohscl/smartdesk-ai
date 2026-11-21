import argparse
import hashlib
import json
from pathlib import Path

from evals.reason_review import (
    ReasonReviewDocument,
    ReviewSummary,
    summarize_reviews,
)


def calculate_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_review_document(
    document: ReasonReviewDocument,
    dataset_path: Path,
    report_path: Path,
) -> None:
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))

    dataset_hash = calculate_sha256(dataset_path)
    report_hash = calculate_sha256(report_path)

    if document.dataset_sha256 != dataset_hash:
        raise ValueError('Hash do dataset não corresponde ao arquivo.')

    if document.report_sha256 != report_hash:
        raise ValueError('Hash do relatório não corresponde ao arquivo.')

    if document.dataset_version != report['dataset_version']:
        raise ValueError('Versão do dataset não corresponde ao relatório.')

    if report['dataset_sha256'] != dataset_hash:
        raise ValueError('Relatório não corresponde ao dataset informado.')

    dataset_ids = {case['id'] for case in dataset}
    report_ids = {result['case_id'] for result in report['results']}
    review_ids = {review.case_id for review in document.reviews}

    if len(dataset_ids) != len(dataset):
        raise ValueError('Dataset contém IDs duplicados.')

    if len(report_ids) != len(report['results']):
        raise ValueError('Relatório contém IDs duplicados.')

    if dataset_ids != report_ids:
        raise ValueError('Dataset e relatório possuem casos diferentes.')

    if not review_ids.issubset(report_ids):
        raise ValueError('Avaliação contém identificadores inexistentes.')


def load_review_document(
    path: Path,
) -> ReasonReviewDocument:
    """Carrega e valida um documento de avaliações humanas."""
    data = json.loads(path.read_text(encoding='utf-8'))

    return ReasonReviewDocument.model_validate(data)


def build_review_summary(
    document: ReasonReviewDocument,
    dataset_path: Path,
    report_path: Path,
) -> ReviewSummary:
    """Valida a integridade e consolida as avaliações."""
    validate_review_document(
        document,
        dataset_path,
        report_path,
    )

    return summarize_reviews(document.reviews)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            'Valida avaliações humanas das justificativas '
            'e apresenta suas métricas.'
        )
    )

    parser.add_argument(
        '--dataset',
        type=Path,
        required=True,
        help='Caminho do dataset original.',
    )
    parser.add_argument(
        '--report',
        type=Path,
        required=True,
        help='Caminho do relatório consolidado.',
    )
    parser.add_argument(
        '--reviews',
        type=Path,
        required=True,
        help='Caminho do JSON de avaliações humanas.',
    )

    args = parser.parse_args()

    document = load_review_document(args.reviews)

    summary = build_review_summary(
        document,
        args.dataset,
        args.report,
    )

    print(summary.model_dump_json(indent=2))


if __name__ == '__main__':
    main()
