import pytest

from app.core.chat_model_policy import (
    ALLOWED_CHAT_MODELS,
    DEFAULT_CHAT_MODEL,
    validate_local_chat_model,
)


def test_chat_model_policy_default():
    assert DEFAULT_CHAT_MODEL == 'qwen2.5:7b'


def test_chat_model_policy_allowlist():
    assert isinstance(ALLOWED_CHAT_MODELS, frozenset)
    assert ALLOWED_CHAT_MODELS == {'qwen2.5:7b'}


def test_chat_model_policy_accepts_approved_model():
    assert validate_local_chat_model('qwen2.5:7b') == 'qwen2.5:7b'


@pytest.mark.parametrize(
    'model',
    [
        'qwen2.5:3b',
        'qwen2.5:latest',
        'qwen2.5:7b-cloud',
        'qwen2.5:7b:cloud',
        'deepseek-r1:7b',
        'gpt-4o',
        'unknown',
        'QWEN2.5:7B',
        'qwen2.5',
        ' qwen2.5:7b ',
        '',
        None,
        True,
        123,
        [],
        {},
    ],
)
def test_chat_model_policy_rejects_unauthorized_models(model):
    with pytest.raises(
        ValueError,
        match='Chat model is not authorized',
    ):
        validate_local_chat_model(model)


def test_chat_model_policy_sanitizes_error():
    model = 'fake-sensitive-model-name'

    with pytest.raises(
        ValueError,
        match='Chat model is not authorized',
    ) as exc_info:
        validate_local_chat_model(model)

    assert model not in str(exc_info.value)
