import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.ai_metrics import AIMetrics, ai_metrics
from app.core.settings import Settings, get_settings

router = APIRouter(
    tags=['Metrics'],
    include_in_schema=False,
)


def get_ai_metrics() -> AIMetrics:
    return ai_metrics


@router.get('/metrics')
async def get_metrics(
    settings: Annotated[Settings, Depends(get_settings)],
    metrics: Annotated[AIMetrics, Depends(get_ai_metrics)],
    token: Annotated[
        str | None,
        Header(alias='X-Metrics-Token'),
    ] = None,
) -> Response:
    if not settings.METRICS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Monitoramento indisponível.',
        )

    if token is None or not secrets.compare_digest(
        token,
        settings.METRICS_TOKEN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso negado.',
        )

    return Response(
        content=generate_latest(metrics.registry),
        media_type=CONTENT_TYPE_LATEST,
    )
