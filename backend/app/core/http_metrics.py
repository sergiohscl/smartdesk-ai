from prometheus_client import CollectorRegistry, Counter, Histogram

from app.core.metrics_registry import metrics_registry


class HTTPMetrics:
    """Coleta métricas operacionais das requisições HTTP."""

    def __init__(
        self,
        registry: CollectorRegistry | None = None,
    ) -> None:
        self.registry = (
            registry if registry is not None else CollectorRegistry()
        )

        self.requests = Counter(
            'smartdesk_http_requests_total',
            'Total de requisicoes HTTP processadas.',
            ['method', 'route', 'status_code'],
            registry=self.registry,
        )

        self.duration = Histogram(
            'smartdesk_http_request_duration_seconds',
            'Duracao das requisicoes HTTP em segundos.',
            ['method', 'route', 'status_code'],
            registry=self.registry,
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
                float('inf'),
            ),
        )

    def record_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        labels = {
            'method': method,
            'route': route,
            'status_code': str(status_code),
        }

        self.requests.labels(**labels).inc()
        self.duration.labels(**labels).observe(duration_seconds)


http_metrics = HTTPMetrics(registry=metrics_registry)
