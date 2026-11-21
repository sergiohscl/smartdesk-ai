import json
from pathlib import Path


def main() -> None:
    dataset_path = Path('evals/independent_dataset_v1.json')
    report_path = Path('evals/reports/independent_consolidated_v1.json')

    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))

    results_by_id = {result['case_id']: result for result in report['results']}

    for case in dataset:
        case_id = case['id']
        result = results_by_id.get(case_id)

        if result is None:
            raise ValueError(f'Resultado não encontrado: {case_id}')

        print('=' * 70)
        print(f'CASO: {case_id}')
        print(f'TÍTULO: {case["title"]}')
        print(f'DESCRIÇÃO: {case["description"]}')
        print()
        print(
            'PRIORIDADE ESPERADA:',
            case['expected_priority'],
        )
        print(
            'PRIORIDADE PREVISTA:',
            result['predicted_priority'],
        )
        print(
            'CATEGORIA ESPERADA:',
            case['expected_category'],
        )
        print(
            'CATEGORIA PREVISTA:',
            result['predicted_category'],
        )
        print()
        print('JUSTIFICATIVA DA IA:')
        print(result['predicted_reason'])
        print()

    print(f'TOTAL DE CASOS: {len(dataset)}')


if __name__ == '__main__':
    main()
