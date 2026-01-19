# Local AI Cybersecurity RAG Lab  
CLI-Only · Native Ollama · Offline-First

This repository documents the setup of a **local, CLI-only AI workstation** designed to support **cybersecurity analysis, research, and future automation** within a broader SOC-focused roadmap.

It is intentionally documented as a **build log**: what was installed, how it was configured, what worked, what failed, and why specific design choices were made.

This project does **not** aim to deliver a product or agent framework. Its purpose is to provide a **reproducible, auditable foundation** for later integration with SOC tooling.

---

## Scope and constraints

- CLI-only operation  
- Native services (no Docker, no cloud APIs)  
- Offline-first by default  
- Explicit tool invocation (no automatic augmentation)  
- Inspectable and user-controlled memory  

Out of scope by design:
- GUIs and dashboards
- OpenWebUI
- Voice input / output
- Autonomous agents
- GPU micro-optimization
- Cloud inference or storage

---

## Core components

- **Ollama (native on Ubuntu)** — local inference engine  
- **Primary model:**  
  - Qwen3-Coder 30B (Q6 quantization)  
- **Custom display:**  
  - adapted for terminal display to enhance readability,
  - answers seprated from user inputs by boxing the answers in colored lines.  
- **Memory layer:**  
  - SQLite (explicit persistence)  
- **RAG roadmap (offline-first):**
  1. Wikipedia (curated / offline)
  2. MITRE ATT&CK
  3. arXiv (titles + abstracts only)
  4. Persistent SQL-backed memory

---

### Design principles

- Native services over containers  
- CLI as the primary interface  
- Tools invoked only when explicitly required  
- No hidden context or silent augmentation  
- Memory operations are explicit and reversible
- Using persistent memory for long term benefits,
- while maintaining the ability to change model but keeping persistent memory.



