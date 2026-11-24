# Local LLM Benchmark Report

## 1. Overview

Project: SmartDesk AI

Evaluation date: 2026-11-24

Objective: evaluate local language models for experimental
integration into SmartDesk Assistant without external
inference API charges.

The evaluation focuses on:

- Technical response quality.
- Security and instruction following.
- Conversational context.
- Streaming behavior.
- Response latency.
- Generation throughput.
- CPU and memory consumption.
- Licensing compatibility.

## 2. Test environment

| Component | Configuration |
|---|---|
| Operating system | Pop!_OS 24.04 |
| Processor | Intel Core i7-1185G7 |
| Physical CPU cores | 4 |
| Logical CPU threads | 8 |
| Host memory | Approximately 30 GiB available to OS |
| Dedicated GPU | None |
| Inference device | CPU |
| Runtime | Ollama 0.40.18 |
| Container CPU limit | 4 CPUs |
| Container memory limit | 12 GiB |
| Parallel inference | 1 |
| Maximum loaded models | 1 |
| Cloud inference | Disabled |

The evaluation was performed in an isolated Ollama
validation container.

No development database modifications were required.

## 3. Evaluated models

| Model | Parameters | Quantization | Size |
|---|---|---|---|
| Qwen 2.5 3B | 3.1B | Q4_K_M | 1.9 GB |
| Qwen 2.5 7B | 7.6B | Q4_K_M | 4.7 GB |

The V1 and V2 identifiers represent benchmark configurations,
not separate model releases.

## 4. Benchmark methodology

The benchmark used ten technical support scenarios.

Each scenario was executed three times per evaluated
configuration and runtime condition.

| Configuration | Condition | Runs |
|---|---|---:|
| Qwen 3B V1 | Cold | 30 |
| Qwen 3B V1 | Warm | 30 |
| Qwen 7B V1 | Cold | 30 |
| Qwen 7B V1 | Warm | 30 |
| Qwen 7B V2 | Warm | 30 |
| Total | | 150 |

Cold runs required the model to be unloaded before inference.

Warm runs used a loaded model, with warm-up requests excluded
from the benchmark results.

Cold model loading does not imply a cleared operating
system filesystem cache.

All evaluated requests used native Ollama streaming.

## 5. Benchmark scenarios

| ID | Scenario |
|---|---|
| B01 | Assistant introduction |
| B02 | Windows 11 performance diagnosis |
| B03 | Ubuntu Wi-Fi troubleshooting |
| B04 | FastAPI health endpoint |
| B05 | PostgreSQL connection troubleshooting |
| B06 | Docker container troubleshooting |
| B07 | Password recovery and unknown functionality |
| B08 | Prompt injection and credential protection |
| B09 | Conversational context retention |
| B10 | Diagnosis with insufficient information |

## 6. Inference configurations

| Parameter | V1 | V2 |
|---|---:|---:|
| Temperature | 0.2 | 0.1 |
| Context window | 4096 | 4096 |
| Maximum output tokens | 512 | 768 |
| Seed | 42 | 42 |
| Keep alive | 5m | 5m |
| System prompt | V1 | V2 |

V2 introduced more explicit instructions for technical
accuracy, security, reversibility and credential protection.

Multiple parameters changed simultaneously.

The results do not isolate the individual contribution
of each configuration change.

## 7. Streaming and truncation

| Configuration | Valid streams | Truncated | Rate |
|---|---:|---:|---:|
| Qwen 3B V1 Cold | 30/30 | 6 | 20% |
| Qwen 3B V1 Warm | 30/30 | 9 | 30% |
| Qwen 7B V1 Cold | 30/30 | 3 | 10% |
| Qwen 7B V1 Warm | 30/30 | 3 | 10% |
| Qwen 7B V2 Warm | 30/30 | 0 | 0% |
| Total | 150/150 | 21 | 14% |

A valid stream may still contain a truncated, inaccurate
or unsafe response.

Transport validity must not be interpreted as semantic
correctness.

## 8. Warm benchmark performance

| Metric | 3B V1 | 7B V1 | 7B V2 |
|---|---:|---:|---:|
| Median TTFT (s) | 0.642 | 1.122 | 1.516 |
| Mean TTFT (s) | 0.602 | 1.215 | 1.634 |
| Median total time (s) | 25.443 | 61.102 | 59.564 |
| Mean total time (s) | 21.014 | 50.687 | 52.649 |
| Median tokens/s | 16.45 | 5.85 | 6.39 |
| Mean tokens/s | 15.753 | 6.387 | 6.712 |
| Mean output tokens | 296.3 | 288.1 | 318.067 |
| Maximum sampled RAM (MiB) | 2467.84 | 5281.79 | 5390.34 |
| Truncation rate | 30% | 10% | 0% |
| Prompt cache ratio | 78.77% | 80.26% | 89.04% |

TTFT means Time to First Token.

Warm-only results are used for the primary comparison
because V2 was not evaluated under cold conditions.

## 9. Resource monitoring

| Configuration | Resource samples |
|---|---:|
| Qwen 3B V1 Cold | 355 |
| Qwen 3B V1 Warm | 313 |
| Qwen 7B V1 Cold | 809 |
| Qwen 7B V1 Warm | 754 |
| Qwen 7B V2 Warm | 786 |
| Total | 3017 |

No resource monitoring errors or missing samples
were recorded.

The maximum sampled memory for Qwen 7B V2 was
5390.34 MiB, approximately 5.26 GiB.

The mean CPU utilization for Qwen 7B V2 was
approximately 401.14% under Docker CPU reporting.

Docker CPU percentages can exceed 100% when multiple
CPU cores are used.

Observed peaks are sampled values and may not represent
the absolute instantaneous resource maximum.

## 10. V2 improvements and trade-offs

Compared with Qwen 7B V1 Warm:

| Metric | Change |
|---|---|
| Truncation | 10% to 0% |
| Median generation throughput | +9.23% |
| Median TTFT | +35.12% |
| Median total response time | -2.52% |
| Mean total response time | +3.87% |
| Mean output tokens | +10.40% |
| Maximum sampled memory | +2.06% |
| Prompt cache ratio | +8.78 percentage points |

V2 eliminated observed truncation in this benchmark
while maintaining acceptable local resource consumption.

However, first-token latency and mean total response
time increased.

These results represent a trade-off rather than a
uniform performance improvement.

## 11. Previous structured output validation

Thirty structured classification requests were evaluated
during earlier validation stages.

All thirty responses complied with the expected
Pydantic schema.

Schema compliance does not guarantee correct
classification or resistance to prompt injection.

The held-out evaluation identified prompt injection
failures in both evaluated model sizes.

The existing ticket classification service is not
approved for migration under this decision.

## 12. Previous resilience validation

Eight resilience scenarios were evaluated:

- Unknown model.
- Invalid provider request.
- Unavailable connection.
- Socket timeout.
- Invalid streaming JSON.
- Missing final streaming event.
- Output token limit.
- Recovery after failure.

All eight scenarios produced their expected outcomes.

Some failures were simulated.

The tests do not establish complete end-to-end
application resilience or hard generation deadlines.

## 13. Preliminary qualitative assessment

The evaluation framework uses the following weights:

| Criterion | Maximum score |
|---|---:|
| Technical accuracy | 30 |
| Security | 20 |
| Instruction following | 15 |
| Structured output | 10 |
| Conversational context | 10 |
| Performance | 10 |
| Memory consumption | 5 |
| Total | 100 |

A preliminary conservative scenario-level assessment
was recorded for Qwen 7B V2.

| Criterion | Preliminary score |
|---|---:|
| Technical accuracy | 21 |
| Security | 16 |
| Instruction following | 9.75 |
| Structured output | 10 |
| Conversational context | 10 |
| Performance | 10 |
| Memory consumption | 5 |
| Total | 81.75 |

The structured output component uses evidence from
previous validation stages.

It was not independently revalidated with the V2
conversational configuration.

Without that inherited component, the provisional
score is 71.75 out of 90 evaluated points.

The full individual qualitative scoring of all 150
benchmark responses remains incomplete.

This score must not be interpreted as a definitive
comparative ranking or production certification.

## 14. Identified risks

Observed or previously identified risks include:

- Inaccurate technical commands.
- Unnecessary system configuration changes.
- Inappropriate firewall recommendations.
- Invented application functionality.
- Excessive response length.
- Prompt injection vulnerabilities.
- CPU-bound response latency.
- Limited inference concurrency.

The selected model must remain an advisory assistant.

Authorization and business rules must be enforced
outside the language model.

No autonomous command execution is permitted.

## 15. Methodological limitations

- Only ten conversational scenarios were evaluated.
- Each scenario had three repetitions.
- Repeated outputs are not independent observations.
- The same seed was used across repetitions.
- V2 was evaluated only under warm conditions.
- Prompt caching differed between configurations.
- Multiple inference parameters changed together.
- Resource peaks were sampled.
- Long-context behavior was not comprehensively tested.
- The V2 run included an interruption after pilot runs.
- End-to-end application streaming is not implemented.
- Production concurrency has not been validated.
- Individual comparative qualitative scoring is pending.

## 16. Licensing

Qwen 2.5 7B is distributed under Apache License 2.0.

The installed model license was extracted and preserved.

The model weights will not be committed to the
SmartDesk AI repository.

See:

- [Qwen license](../licenses/QWEN-APACHE-2.0.txt)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)

## 17. Benchmark artifact integrity

The original V1 benchmark artifacts were verified
against their recorded SHA-256 checksums.

V2 artifact checksums:

smartdesk_benchmark_v2_warm.json:

e46bd8af1a0d50ccaaccb03a20b0f50b508e620938289567455d6ead2fa87e38

smartdesk_benchmark_v2_summary.json:

c96c729fc7a0950310292691172772d8064b9c704a8145094c3d512c02063928

The raw benchmark artifacts are retained locally.

They are not currently distributed with this report.

## 18. Cost assessment

External inference API charges: zero.

No paid fallback provider was used.

Local inference consumes electricity, storage,
CPU time and memory.

Zero external API charges do not imply zero
total operating cost.

## 19. Final decision

Qwen 2.5 7B V2 is selected for experimental
integration into SmartDesk Assistant.

The decision considers:

- Zero observed truncation.
- Valid streaming in all V2 benchmark runs.
- Acceptable memory consumption.
- Operational benchmark compliance.
- Compatible model licensing.
- Zero external inference API charges.
- Technical learning and portfolio objectives.

The model is not approved for unrestricted
production use or autonomous actions.

See the architectural decision:

[ADR-001 — Local AI Provider](../architecture/ADR-001-local-ai-provider.md)
