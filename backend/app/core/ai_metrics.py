from prometheus_client import CollectorRegistry, Counter, Histogram

from app.core.metrics_registry import metrics_registry


class AIMetrics:
    """Coleta métricas operacionais das classificações da IA."""

    def __init__(
        self,
        registry: CollectorRegistry | None = None,
    ) -> None:
        self.registry = (
            registry if registry is not None else CollectorRegistry()
        )

        self.classifications = Counter(
            'smartdesk_ai_classifications_total',
            'Total de classificacoes realizadas pela IA.',
            ['outcome', 'model', 'prompt_version'],
            registry=self.registry,
        )

        self.duration = Histogram(
            'smartdesk_ai_classification_duration_seconds',
            'Duracao das classificacoes da IA em segundos.',
            ['outcome', 'model', 'prompt_version'],
            registry=self.registry,
            buckets=(
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
                15.0,
                30.0,
                float('inf'),
            ),
        )

        self.errors = Counter(
            'smartdesk_ai_errors_total',
            'Total de erros de classificacao por categoria.',
            ['error_category', 'model', 'prompt_version'],
            registry=self.registry,
        )

    def record_classification(
        self,
        *,
        outcome: str,
        duration_seconds: float,
        model: str,
        prompt_version: str,
        error_category: str | None = None,
    ) -> None:
        labels = {
            'outcome': outcome,
            'model': model,
            'prompt_version': prompt_version,
        }

        self.classifications.labels(**labels).inc()
        self.duration.labels(**labels).observe(duration_seconds)

        if outcome == 'error' and error_category is not None:
            self.errors.labels(
                error_category=error_category,
                model=model,
                prompt_version=prompt_version,
            ).inc()


ai_metrics = AIMetrics(registry=metrics_registry)
