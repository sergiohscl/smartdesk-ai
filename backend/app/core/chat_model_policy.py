DEFAULT_CHAT_MODEL = 'qwen2.5:7b'

ALLOWED_CHAT_MODELS = frozenset({
    DEFAULT_CHAT_MODEL,
})


def validate_local_chat_model(model: str) -> str:
    """Reject models outside the approved local model policy."""

    if not isinstance(model, str) or model not in ALLOWED_CHAT_MODELS:
        raise ValueError('Chat model is not authorized.')

    return model
