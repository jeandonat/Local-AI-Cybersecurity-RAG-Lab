# Decision log

## Why native Ollama (final choice)
- Fewer moving parts than containerized inference
- Avoids port binding conflicts and Docker image/version tag confusion
- Simple model storage at `~/.ollama/`

## Why CLI
- More support for tools than GUI like openwebui
- Built-in Knowledge Base support for RAG


## Why Qwen3-coder 30B quant 6
- Best option for my hardware
- Qwen: excellent structured reasoning and technical depth (cyber + code)

## Out of scope (by design)
- Voice I/O (added later if needed)
- Aggressive GPU tuning / benchmarking (kept stable)
