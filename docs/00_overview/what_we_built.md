# What we built

This repo documents a local AI workstation configured for:

1. **Native Ollama** running as the local inference server on port `11434`.
2. **OpenWebUI** running locally on port `3000` and configured to talk to Ollama.
3. **Multiple local models installed** (Llama 3.1 13B + Qwen 2.5 14B).
4. A custom Ollama persona model (**JD Master**) built via a `Modelfile`.
5. A planned **RAG** knowledge base:
   - Wikipedia first (offline reference)
   - MITRE ATT&CK second (tactics/techniques/detections)

This is meant as a recruiter-friendly “lab notebook”: reproducible steps, commands, and evidence.
