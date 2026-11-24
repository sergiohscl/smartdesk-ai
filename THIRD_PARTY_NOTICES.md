# Third-Party Notices

SmartDesk AI is licensed under the MIT License.

Third-party components remain subject to their respective licenses.
The MIT License of this project does not replace or modify those licenses.

## Qwen 2.5 7B Instruct

- Developer: Alibaba Cloud
- Copyright: 2024 Alibaba Cloud
- License: Apache License 2.0
- Model: qwen2.5:7b
- Architecture: qwen2
- Parameters: 7.6B
- Format: GGUF
- Quantization: Q4_K_M
- Provider: Ollama
- Integration status: experimental, planned

### Validated model digest

845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e

### References

- Model repository:
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

- Ollama model:
  https://ollama.com/library/qwen2.5:7b

- Apache License 2.0:
  https://www.apache.org/licenses/LICENSE-2.0

- Preserved model license:
  [QWEN-APACHE-2.0.txt](docs/licenses/QWEN-APACHE-2.0.txt)

### Distribution

SmartDesk AI does not redistribute the model weights in its Git repository.

The model is obtained separately through Ollama.

The project is independent and is not affiliated with or endorsed by
Alibaba Cloud or Ollama.

## Ollama

Ollama is an external runtime selected for the experimental local AI
integration.

- Repository: https://github.com/ollama/ollama
- License: MIT
- Validated runtime version: 0.40.18

Ollama is distributed separately from the SmartDesk AI source code.

## Other dependencies

Backend, frontend and infrastructure dependencies remain subject to
their respective licenses.

Dependency information is maintained in the project's dependency manifests,
lockfiles and container image definitions.

This document is not an exhaustive third-party license audit.
