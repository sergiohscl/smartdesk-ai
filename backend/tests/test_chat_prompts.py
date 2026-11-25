import pytest

from app.services.chat_prompts import (
    CHAT_SYSTEM_PROMPT_V2,
    build_system_message,
    get_chat_system_prompt,
)
from app.services.providers.base import ProviderRole


def test_get_versioned_system_prompt():
    prompt = get_chat_system_prompt('v2')

    assert prompt == CHAT_SYSTEM_PROMPT_V2
    assert 'SmartDesk Assistant' in prompt
    assert prompt.strip()


def test_reject_unsupported_prompt_version():
    with pytest.raises(
        ValueError,
        match='Unsupported chat prompt version.',
    ):
        get_chat_system_prompt('unknown')


def test_build_system_message():
    message = build_system_message('v2')

    assert message.role is ProviderRole.SYSTEM
    assert message.content == CHAT_SYSTEM_PROMPT_V2
