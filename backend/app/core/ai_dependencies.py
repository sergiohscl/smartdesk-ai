from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from openai import AsyncOpenAI

from app.core.settings import Settings, get_settings
from app.services.ai_service import AIService


async def get_ai_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AIService]:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Serviço de análise com IA indisponível.',
        )

    async with AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        max_retries=0,
    ) as client:
        yield AIService(
            client=client,
            settings=settings,
        )
