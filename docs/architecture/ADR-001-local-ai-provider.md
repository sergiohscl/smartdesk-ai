# ADR-001 — Local AI Provider for SmartDesk Assistant

## Status

Accepted for experimental integration.

Date: 2026-11-24

## Context

SmartDesk AI is a full-stack portfolio project focused on
technical support ticket management, software architecture,
security, observability and artificial intelligence.

The next development phase introduces SmartDesk Assistant,
a conversational assistant for technical support.

The project prioritizes:

- Technical learning.
- Zero external API charges for the assistant.
- Local inference.
- Reproducible infrastructure.
- Provider-independent architecture.
- Security and privacy.
- Automated testing without external AI calls.
- Preservation of the development database.

The existing OpenAI-based ticket classification service
remains outside the scope of this migration.

## Decision

Use Ollama as the local inference provider and Qwen 2.5 7B
as the experimental conversational model.

The selected configuration is identified internally as V2.
V2 refers to the benchmark prompt and inference settings,
not a different release of the Qwen model.

No automatic fallback to paid AI providers is permitted.

## Evaluated alternatives

### External OpenAI API

Advantages:

- Managed inference infrastructure.
- Reduced local hardware requirements.
- Existing integration in SmartDesk AI.

Disadvantages:

- Potential API charges.
- External service dependency.
- Network dependency.
- External processing of submitted information.

Decision: not selected for the new assistant.

### Qwen 2.5 3B

Advantages:

- Lower memory consumption.
- Higher generation throughput.
- Lower response latency.

Disadvantages:

- Higher observed truncation rate.
- Technical inaccuracies.
- Unsafe recommendations in selected scenarios.
- Additional licensing considerations.

Decision: not selected for the initial integration.

### Qwen 2.5 7B V1

Advantages:

- Lower truncation rate than the 3B configuration.
- Better behavior in selected technical scenarios.
- Apache License 2.0.

Disadvantages:

- Higher memory consumption.
- Lower generation throughput.
- Truncated responses.
- Technical and security limitations.

Decision: superseded by the experimental V2 configuration.

### Qwen 2.5 7B V2

Advantages:

- Zero observed truncation in 30 warm benchmark runs.
- Valid streaming in all 30 benchmark runs.
- Acceptable local memory consumption.
- Apache License 2.0.
- No external inference API charges.

Disadvantages:

- CPU-bound inference.
- Higher latency than the 3B model.
- Potential hallucinations.
- Potentially unsafe technical recommendations.
- Limited context window in the selected configuration.

Decision: selected for experimental integration.

## Model identification

- Provider: Ollama
- Runtime version: 0.40.18
- Model: qwen2.5:7b
- Architecture: qwen2
- Parameters: 7.6B
- Format: GGUF
- Quantization: Q4_K_M
- Native context length: 32768 tokens
- License: Apache License 2.0
- Copyright: 2024 Alibaba Cloud

Model digest:

845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e

## Selected configuration

| Parameter | Value |
|---|---|
| Temperature | 0.1 |
| Context window | 4096 tokens |
| Maximum output | 768 tokens |
| Seed | 42 |
| Keep alive | 5 minutes |
| Global generation timeout | 120 seconds |
| CPU limit | 4 CPUs |
| Memory limit | 12 GiB |
| Parallel inference | 1 |
| Maximum loaded models | 1 |
| Cloud inference | Disabled |
| Paid fallback | Disabled |

The generation timeout is an implementation requirement,
not a previously validated hard deadline.

The maximum theoretical input budget is 3328 tokens.
The system prompt, conversation history, current message
and model template overhead must fit within this budget.

## Architecture

The proposed integration follows this flow:

Frontend
  -> FastAPI
  -> ChatService
  -> AIProvider
  -> OllamaProvider
  -> Ollama
  -> Qwen 2.5 7B

The provider abstraction must prevent application business
logic from depending directly on Ollama-specific contracts.

PostgreSQL remains the source of truth for conversations,
messages, generation state and usage information.

## Streaming

The planned streaming flow is:

Ollama NDJSON
  -> OllamaProvider
  -> ChatService
  -> FastAPI Server-Sent Events
  -> Nginx
  -> React Fetch ReadableStream

The implementation must support:

- Incremental response delivery.
- Generation cancellation.
- Partial response persistence.
- Truncated response identification.
- Provider error handling.
- Generation timeout.
- Recovery from interrupted generations.

End-to-end application streaming remains to be implemented.

## Security

The assistant must enforce the following protection layers:

1. Authentication and authorization.
2. Input validation.
3. Conversation ownership and privacy.
4. Usage and concurrency limits.
5. Controlled conversational context.
6. Local provider without autonomous tools.
7. Safe output handling.
8. Explicit human confirmation for ticket creation.
9. Observability without sensitive data exposure.

The assistant must not:

- Execute operating system commands.
- Execute SQL statements.
- Access arbitrary application records.
- Request credentials.
- Assume administrative privileges.
- Modify tickets autonomously.
- Create tickets without explicit confirmation.
- Access conversations belonging to other users.

Prompt instructions alone are not a security boundary.

Application authorization and deterministic business rules
must remain independent of model-generated content.

## Usage limits

| Parameter | Value |
|---|---|
| Maximum message length | 8000 characters |
| Maximum title length | 150 characters |
| Maximum context messages | 20 |
| Daily requests per user | 50 |
| Requests per minute per user | 5 |
| Concurrent generations per user | 1 |
| Concurrent generations globally | 1 |

These limits are approved design requirements and remain
subject to implementation and automated validation.

## Benchmark evidence

The evaluation included:

- 60 cold benchmark runs.
- 60 warm V1 benchmark runs.
- 30 warm V2 benchmark runs.
- 3017 resource monitoring samples.

Selected V2 results:

| Metric | Result |
|---|---|
| Valid streaming | 30/30 |
| Observed truncation | 0/30 |
| Median time to first token | 1.516 seconds |
| Median generation throughput | 6.39 tokens/second |
| Median total response time | 59.564 seconds |
| Maximum sampled memory | 5390.34 MiB |
| External inference API charges | Zero |

The V2 configuration met the operational benchmark criteria.

The qualitative assessment remains provisional.
Operational success does not establish semantic correctness
or unrestricted production readiness.

Previous structured classification tests demonstrated
schema compliance but also identified prompt injection
vulnerabilities.

The existing ticket classification service will not be
migrated as part of this decision.

## Consequences

### Positive

- No external inference API charges for the local assistant.
- Greater control over inference infrastructure.
- Reduced dependency on external AI services.
- Practical experience with local language models.
- Provider-independent application architecture.
- Reproducible technical evaluation.

### Negative

- Increased local CPU and memory consumption.
- Longer response times.
- Limited concurrent inference capacity.
- Additional infrastructure maintenance.
- Potentially inaccurate or unsafe model responses.
- Need for deterministic application safeguards.

Local inference still consumes electricity and hardware
resources. Zero API charges do not imply zero total cost.

## Testing strategy

Automated tests must use mocked AI providers.

The test suite must not:

- Invoke real paid AI APIs.
- Require downloading language models.
- Require a running Ollama instance.
- Create a separate test database.
- Modify development database records.

Integration and concurrency guarantees must be validated
separately under controlled conditions.

## Licensing

SmartDesk AI source code: MIT License.

Qwen 2.5 7B: Apache License 2.0.

The model weights will not be committed to the repository.

Third-party components retain their respective licenses.

See:

- [Project license](../../LICENSE)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)
- [Qwen license](../licenses/QWEN-APACHE-2.0.txt)

## Scope exclusions

The following capabilities are outside the current scope:

- RAG.
- Vector databases.
- MCP integrations.
- Autonomous agents.
- Web browsing.
- Command execution.
- Voice interactions.
- File attachments.
- Automatic migration of the existing classifier.

## Final decision

Qwen 2.5 7B V2 is approved for experimental integration
into SmartDesk Assistant through Ollama.

This decision does not constitute unrestricted production
approval.

The integration must preserve human control, application
authorization, local inference and zero external API charges.
