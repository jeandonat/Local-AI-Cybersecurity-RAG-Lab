# Native Ollama installation

## Install
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Start / verify
```bash
ollama --version
curl -s http://localhost:11434/api/tags | head
```

## Service management (if installed as systemd service)
```bash
systemctl status ollama
sudo systemctl enable --now ollama
```

## Model storage
Native models are stored in:
- `~/.ollama/models`
