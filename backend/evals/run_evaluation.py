import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock

from openai import AsyncOpenAI

from app.core.settings import get_settings
from app.models.ticket import TicketPriority
from app.schemas.ai import AIClassification, AITicketCategory
from app.services.ai_service import (
    CLASSIFICATION_INSTRUCTIONS,
    CLASSIFICATION_PROMPT_VERSION,
    AIService,
)
from evals.report import serialize_report
from evals.runner import EvaluationCase, evaluate_cases

DATASET_PATH = Path(__file__).with_name('golden_dataset.json')
POLICY_PATH = Path(__file__).with_name('classification_policy.md')
REPORTS_DIR = Path(__file__).with_name('reports')
INDEPENDENT_DATASET_PATH = Path(__file__).with_name(
    'independent_dataset_v1.json'
)

DATASET_PATHS = {
    'golden': DATASET_PATH,
    'independent': INDEPENDENT_DATASET_PATH,
}


def calculate_dataset_hash(
    dataset: str = 'golden',
) -> str:
    if dataset not in DATASET_PATHS:
        raise ValueError('Dataset inválido.')

    content = DATASET_PATHS[dataset].read_bytes()
    return hashlib.sha256(content).hexdigest()


def calculate_prompt_hash() -> str:
    return hashlib.sha256(
        CLASSIFICATION_INSTRUCTIONS.encode('utf-8')
    ).hexdigest()


def calculate_policy_hash() -> str:
    content = POLICY_PATH.read_bytes()
    return hashlib.sha256(content).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Avaliação de classificações do SmartDesk AI.'
    )
    parser.add_argument(
        '--mode',
        choices=['mock', 'real'],
        default='mock',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=5,
    )
    parser.add_argument(
        '--start',
        type=int,
        default=1,
        help='Posição inicial do dataset, começando em 1.',
    )
    parser.add_argument(
        '--confirm-api-cost',
        action='store_true',
    )
    parser.add_argument(
        '--dataset',
        choices=['golden', 'independent'],
        default='golden',
        help='Dataset utilizado na avaliação.',
    )
    return parser.parse_args()


def load_cases(
    limit: int,
    start: int = 1,
    dataset: str = 'golden',
) -> list[EvaluationCase]:
    if dataset not in DATASET_PATHS:
        raise ValueError('Dataset inválido.')

    dataset_path = DATASET_PATHS[dataset]

    if not dataset_path.is_file():
        raise FileNotFoundError(f'Dataset não encontrado: {dataset_path}')

    data = json.loads(dataset_path.read_text(encoding='utf-8'))

    total_cases = len(data)

    if limit < 1 or limit > total_cases:
        raise ValueError(f'O limite deve estar entre 1 e {total_cases}.')

    if start < 1 or start > total_cases:
        raise ValueError(f'O início deve estar entre 1 e {total_cases}.')

    if start + limit - 1 > total_cases:
        raise ValueError(
            f'O intervalo solicitado excede os {total_cases} casos.'
        )

    return data[start - 1 : start - 1 + limit]  # noqa E203


def build_mock_service() -> AIService:
    service = MagicMock(spec=AIService)

    service.analyze_ticket = AsyncMock(
        return_value=AIClassification(
            suggested_category=AITicketCategory.NETWORK,
            suggested_priority=TicketPriority.HIGH,
            reason='Resposta simulada.',
        )
    )
    return cast(AIService, service)


async def run() -> None:
    args = parse_args()

    if args.mode == 'real' and not args.confirm_api_cost:
        raise SystemExit('Modo real exige --confirm-api-cost.')

    cases = load_cases(
        args.limit,
        args.start,
        args.dataset,
    )
    settings = get_settings()

    if args.mode == 'real':
        if not settings.OPENAI_API_KEY:
            raise SystemExit('OPENAI_API_KEY não configurada.')

        async with AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            max_retries=0,
        ) as client:
            service = AIService(client=client, settings=settings)
            report = await evaluate_cases(service, cases)
    else:
        service = build_mock_service()
        report = await evaluate_cases(service, cases)

    data = serialize_report(
        report=report,
        model=(settings.OPENAI_MODEL if args.mode == 'real' else 'mock-model'),
        dataset_version=(
            'golden-v1' if args.dataset == 'golden' else 'independent-v1'
        ),
        prompt_version=CLASSIFICATION_PROMPT_VERSION,
    )

    data['mode'] = args.mode
    data['dataset_sha256'] = calculate_dataset_hash(args.dataset)
    data['dataset_name'] = args.dataset
    data['prompt_sha256'] = calculate_prompt_hash()
    data['policy_sha256'] = calculate_policy_hash()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output_path = REPORTS_DIR / (f'evaluation_{args.mode}_{timestamp}.json')

    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    print(f'Relatório: {output_path}')
    print(f'Casos: {report.total_cases}')
    print(f'Taxa de sucesso: {report.success_rate:.2%}')

    if report.metrics is not None:
        print(f'Acurácia completa: {report.metrics.full_accuracy:.2%}')
    else:
        print('Acurácia completa: indisponível')


if __name__ == '__main__':
    asyncio.run(run())
