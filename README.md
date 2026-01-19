# Local AI Cybersecurity RAG Lab  
CLI-Only · Native Ollama · Offline-First

This repository documents the setup of a **local, CLI-only AI workstation** designed to support **cybersecurity analysis, research, and future automation** within a broader SOC-focused roadmap.

---

## Core components

- **Ollama (native on Ubuntu)** — local inference engine  
- **Primary model:** Qwen3-Coder 30B (Q6 quantization)  
- **Memory layer:** SQLite (explicit persistence)  
- **RAG sources (offline-first):**
  - Wikipedia (curated / offline)
  - MITRE ATT&CK
  - arXiv (titles + abstracts only)

---

## Components used

This lab uses the following tools (pinned versions recommended):

- **jarvis-cli** — CLI interface and tool routing  
- **rag-folder-tool** — dataset ingestion / indexing  
- **kiwix-wrapper** — offline Wikipedia access  
- **arxiv-tool** — arXiv abstracts ingestion / search  

---

## Design principles

- Native services over containers  
- CLI as the primary interface  
- Tools invoked only when explicitly required  
- No hidden context or silent augmentation  
- Memory operations are explicit and reversible  
- Persistent memory enables long-term workflows while keeping model choice flexible  

**Terminal output formatting (quality-of-life):**  
Optional formatting to improve readability (clear separation between user input and model output, boxed output).

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
