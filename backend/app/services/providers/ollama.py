from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import override

import httpx

from app.core.chat_model_policy import validate_local_chat_model
from app.core.ollama_url_policy import validate_local_ollama_url
from app.core.settings import Settings
from app.services.providers.base import (
    AIProvider,
    ProviderCompletion,
    ProviderDelta,
    ProviderEvent,
    ProviderRequest,
)
from app.services.providers.exceptions import (
    ProviderError,
    ProviderErrorCode,
)
from app.services.providers.ndjson import parse_ndjson_line
from app.services.providers.ndjson_stream import iter_ndjson_lines
from app.services.providers.ollama_errors import classify_httpx_error
from app.services.providers.ollama_events import parse_ollama_event
from app.services.providers.ollama_http import validate_ollama_response


async def _iter_response_events(
    response: httpx.Response,
    expected_model: str,
) -> AsyncIterator[ProviderEvent]:
    """Convert validated NDJSON lines into provider events."""

    async with aclosing(iter_ndjson_lines(response.aiter_raw())) as lines:
        async for line in lines:
            data = parse_ndjson_line(line)

            if data is None:
                continue

            events = parse_ollama_event(
                data,
                expected_model=expected_model,
            )

            for event in events:
                yield event

                if isinstance(event, ProviderCompletion):
                    return

    raise ProviderError(ProviderErrorCode.STREAM_INTERRUPTED)


class OllamaProvider(AIProvider):
    """Local AI provider backed by the Ollama HTTP API."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    @property
    @override
    def model(self) -> str:
        return validate_local_chat_model(self._settings.CHAT_MODEL)

    def _build_payload(
        self,
        request: ProviderRequest,
    ) -> dict[str, object]:
        return {
            'model': self.model,
            'messages': [
                {
                    'role': message.role.value,
                    'content': message.content,
                }
                for message in request.messages
            ],
            'stream': True,
            'keep_alive': self._settings.OLLAMA_KEEP_ALIVE,
            'options': {
                'temperature': self._settings.OLLAMA_TEMPERATURE,
                'num_ctx': self._settings.OLLAMA_NUM_CTX,
                'num_predict': self._settings.OLLAMA_NUM_PREDICT,
                'seed': self._settings.OLLAMA_SEED,
            },
        }

    def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=str(
                validate_local_ollama_url(self._settings.OLLAMA_BASE_URL)
            ),
            timeout=httpx.Timeout(
                float(self._settings.CHAT_TIMEOUT_SECONDS),
                connect=5.0,
            ),
            follow_redirects=False,
            trust_env=False,
            transport=self._transport,
        )

    async def _stream_http(
        self,
        request: ProviderRequest,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream validated events from the local Ollama API."""

        payload = self._build_payload(request)
        expected_model = validate_local_chat_model(payload['model'])

        async with self._create_client() as client:
            async with client.stream(
                'POST',
                '/api/chat',
                json=payload,
                headers={
                    'Accept': 'application/x-ndjson',
                    'Accept-Encoding': 'identity',
                },
                follow_redirects=False,
            ) as response:
                validate_ollama_response(response)

                async with aclosing(
                    _iter_response_events(
                        response,
                        expected_model,
                    )
                ) as events:
                    async for event in events:
                        yield event

    @override
    async def stream(
        self,
        request: ProviderRequest,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream events with sanitized transport error handling."""

        content_started = False

        try:
            async with aclosing(self._stream_http(request)) as events:
                async for event in events:
                    if isinstance(event, ProviderDelta):
                        content_started = True

                    yield event

        except httpx.RequestError as error:
            raise ProviderError(
                classify_httpx_error(
                    error,
                    content_started=content_started,
                )
            ) from None
