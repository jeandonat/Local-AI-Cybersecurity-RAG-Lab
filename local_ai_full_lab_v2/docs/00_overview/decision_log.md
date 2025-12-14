# Decision log

## Why native Ollama (final choice)
- Fewer moving parts than containerized inference
- Avoids port binding conflicts and Docker image/version tag confusion
- Simple model storage at `~/.ollama/`

## Why OpenWebUI
- Simple UI for multi-model workflows
- Built-in Knowledge Base support for RAG
- Easy persona/model switching

## Why Llama 3.1 13B + Qwen 2.5 14B
- Llama: strong general assistant and synthesis
- Qwen: excellent structured reasoning and technical depth (cyber + code)

## Out of scope (by design)
- Voice I/O (added later if needed)
- Aggressive GPU tuning / benchmarking (kept stable)
