# Model installation

> Exact tags can evolve. Use the tags that exist in your Ollama registry.

## Llama 3.1 (13B)
```bash
ollama pull llama3.1:13b
```

## Qwen 2.5 (14B)
```bash
ollama pull qwen2.5:14b
```

## List installed
```bash
ollama list
```

## Sanity run
```bash
ollama run llama3.1:13b "Write a 5-line summary of MITRE ATT&CK."
ollama run qwen2.5:14b "Explain the difference between TTPs and IOCs."
```
