from evals.run_evaluation import POLICY_PATH


def load_policy() -> str:
    return POLICY_PATH.read_text(encoding='utf-8')


def test_policy_defines_medium_with_alternative():
    policy = load_policy()

    assert 'funcionalidade relevante degradada' in policy
    assert 'alternativa operacional disponível' in policy
    assert 'prioridade medium' in policy


def test_policy_defines_critical_for_essential_operations():
    policy = ' '.join(load_policy().split())

    assert 'paralisação completa de uma operação essencial' in policy
    assert 'alternativa operacional viável' in policy
    assert 'prioridade critical' in policy


def test_policy_does_not_automatically_lower_priority():
    policy = load_policy()

    assert 'Não reduzir automaticamente a prioridade' in policy


def test_policy_does_not_automatically_raise_priority():
    policy = load_policy()

    assert 'Não elevar automaticamente a prioridade' in policy


def test_policy_requires_combined_impact_analysis():
    policy = load_policy()

    for criterion in (
        'abrangência',
        'relevância da atividade',
        'interrupção',
        'alternativas',
        'urgência',
    ):
        assert criterion in policy
