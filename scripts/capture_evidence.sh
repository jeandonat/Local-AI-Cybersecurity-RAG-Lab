#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/docs/_evidence/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$OUT_DIR"

echo "[*] Writing evidence to: $OUT_DIR"

# Basic system info
{
  echo "== date =="; date
  echo
  echo "== uname =="; uname -a
  echo
  echo "== disk =="; df -h
  echo
  echo "== lsblk =="; lsblk -o NAME,MODEL,TRAN,ROTA,SIZE,MOUNTPOINT
} > "$OUT_DIR/system.txt" 2>&1 || true

# Ollama info
{
  echo "== ollama version =="; ollama --version
  echo
  echo "== ollama list =="; ollama list
  echo
  echo "== ollama tags api (first lines) =="; curl -s http://localhost:11434/api/tags | head -c 2000; echo
} > "$OUT_DIR/ollama.txt" 2>&1 || true

# Services
{
  echo "== systemctl ollama =="; systemctl status ollama --no-pager || true
  echo
  echo "== user systemctl openwebui =="; systemctl --user status openwebui.service --no-pager || true
} > "$OUT_DIR/services.txt" 2>&1 || true

echo "[+] Done."
echo "    You can commit docs/_evidence/* to GitHub (it contains no model blobs)."
