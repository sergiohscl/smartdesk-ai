from unittest.mock import MagicMock

import pytest
from pydantic_settings import SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat_dependencies import (
    get_chat_provider,
    get_chat_service,
)
from app.core.settings import Settings
from app.services.chat_service import ChatService
from app.services.providers import AIProvider, OllamaProvider


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_CHAT_DEP_TEST_',
    )


@pytest.fixture
def settings():
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://fake:fake@localhost/fake',
        JWT_SECRET_KEY='fake-test-secret',
    )


def test_get_chat_provider(settings):
    provider = get_chat_provider(settings)

    assert isinstance(provider, OllamaProvider)
    assert provider.model == settings.CHAT_MODEL


def test_get_chat_service(settings):
    session = MagicMock(spec=AsyncSession)
    provider = MagicMock(spec=AIProvider)

    service = get_chat_service(
        session=session,
        settings=settings,
        provider=provider,
    )

    assert isinstance(service, ChatService)
