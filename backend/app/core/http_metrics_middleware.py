from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.http_metrics import HTTPMetrics


class HTTPMetricsMiddleware:
    """Registra métricas HTTP sem alterar as respostas da aplicação."""

    def __init__(
        self,
        app: ASGIApp,
        metrics: HTTPMetrics,
    ) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '')

        if path == '/api/v1/metrics':
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message['type'] == 'http.response.start':
                status_code = message['status']

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get('route')
            route_path = getattr(route, 'path', None)

            if route_path is None:
                route_path = 'unmatched'

            self.metrics.record_request(
                method=scope['method'],
                route=route_path,
                status_code=status_code,
                duration_seconds=perf_counter() - started_at,
            )
