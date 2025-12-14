# Docker reference (historical / optional)

During experimentation, Docker was used to try containerized Ollama/OpenWebUI.
This often introduces extra failure modes:

- Port conflicts (`11434` already bound)
- Image/tag confusion (Docker tags ≠ internal Ollama versions)
- GPU runtime differences

Final build uses: **native Ollama**.

This file is kept as a record of the exploration path.
