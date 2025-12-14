# Prerequisites

## System
- Ubuntu Desktop
- Sufficient disk space:
  - Models (Llama 13B + Qwen 14B): plan **25–40 GB** headroom
  - RAG datasets later (Wikipedia can be 40+ GB depending on format)

## Useful checks
```bash
df -h
lsblk -o NAME,MODEL,TRAN,ROTA,SIZE,MOUNTPOINT
```

## Freeing space (common win)
Steam/Proton games can take 100+ GB. Removing one large game often frees enough space for multiple LLMs.
