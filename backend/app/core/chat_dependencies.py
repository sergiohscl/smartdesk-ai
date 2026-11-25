from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.settings import Settings, get_settings
from app.services.chat_service import ChatService
from app.services.providers import AIProvider, OllamaProvider

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_chat_provider(
    settings: SettingsDep,
) -> AIProvider:
    """Provide the configured local AI provider."""

    return OllamaProvider(settings)


ChatProviderDep = Annotated[
    AIProvider,
    Depends(get_chat_provider),
]


def get_chat_service(
    session: SessionDep,
    settings: SettingsDep,
    provider: ChatProviderDep,
) -> ChatService:
    """Provide a chat service with injected dependencies."""

    return ChatService(
        session=session,
        settings=settings,
        provider=provider,
    )


ChatServiceDep = Annotated[
    ChatService,
    Depends(get_chat_service),
]
