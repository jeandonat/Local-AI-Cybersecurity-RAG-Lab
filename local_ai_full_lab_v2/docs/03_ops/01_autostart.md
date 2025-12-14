# Autostart on reboot (native stack)

## 1) Ollama autostart
If Ollama is installed as a systemd service:

```bash
sudo systemctl enable --now ollama
systemctl status ollama
```

If it is NOT a service on your system, you can create one (see `scripts/systemd/ollama.service`).

## 2) OpenWebUI autostart (user service)

Create a user service:

- `~/.config/systemd/user/openwebui.service`

Example service file is provided at:
- `scripts/systemd/openwebui.service`

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now openwebui.service
systemctl --user status openwebui.service
```

> If you installed OpenWebUI via Docker instead, do not use the user service—use Docker’s restart policy.

## 3) Verify after reboot

```bash
curl -s http://localhost:11434/api/tags | head
curl -I http://localhost:3000
```
