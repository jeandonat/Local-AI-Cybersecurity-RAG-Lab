# Troubleshooting

## OpenWebUI can’t see models
- Confirm API base: `http://localhost:11434`
- Verify Ollama is running:
  ```bash
  curl -s http://localhost:11434/api/tags | head
  ```

## Port already in use
Check who uses port 11434:
```bash
sudo lsof -i :11434
```

## Disk space
Large games / Proton prefixes can consume 100+ GB.
Docker images can also bloat disk.
