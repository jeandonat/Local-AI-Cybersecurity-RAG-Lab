# Local AI Cybersecurity RAG Lab (Native Ollama + OpenWebUI)

A **GitHub-documented build log** of a full local AI workstation:

- **Ollama (native on Ubuntu)** as the primary inference server
- **OpenWebUI** as the UI + model selector + Knowledge Base (RAG)
- **Models installed locally:**
  - **Llama 3.1 (13B)**
  - **Qwen 2.5 (14B)**
  - (Optional) Mistral / TinyLlama for lightweight tasks
- **JD Master persona** built as an Ollama custom model
- **RAG roadmap:** Wikipedia first → MITRE ATT&CK second

> This repo intentionally excludes: voice features, “GPU tweaking”, and non-essential optimization.  
> Goal: **reproducible**, **stable**, **recruiter-readable** documentation.

---

## What you’ll find here

- A **complete install + configuration guide**
- A “what actually happened” **build log** (including mistakes + fixes)
- Scripts to **capture evidence** (versions, models, systemd status) for GitHub
- A clean place to add **RAG datasets** later (Wikipedia, MITRE ATT&CK)

---

## Architecture (final)

```text
Browser :3000  ──►  OpenWebUI  ──►  Ollama (native)  ──►  Models stored in ~/.ollama
                  (Knowledge Base / RAG later)
```

### Why “native Ollama”?
- Avoids Docker networking edge cases
- Simplifies model storage
- Easier autostart and updates
- Fewer moving parts

---

## Quickstart (verify your system)

```bash
ollama --version
ollama list
curl -s http://localhost:11434/api/tags | head
```

Open OpenWebUI and set **Ollama API Base** to:

- `http://localhost:11434`

---

## Models

Recommended “two-model strategy”:

- **Llama 3.1 (13B)** → general reasoning + synthesis
- **Qwen 2.5 (14B)** → technical depth (cyber, scripting, structured analysis)

Install docs: `docs/01_installation/03_models.md`

---

## JD Master persona

- Persona file: `personas/jd-master/Modelfile`
- Build: `ollama create jd-master -f personas/jd-master/Modelfile`

Docs: `docs/01_installation/04_persona.md`

---

## RAG roadmap

- Wikipedia (offline) → `docs/02_rag/01_wikipedia.md`
- MITRE ATT&CK (offline) → `docs/02_rag/02_mitre_attack.md`

---

## Autostart

Docs: `docs/03_ops/01_autostart.md`

---

## Evidence capture (highly recommended)

Run this after each milestone to generate shareable evidence files:

```bash
bash scripts/capture_evidence.sh
```

Outputs go to: `docs/_evidence/`

---

## Repo layout

```text
docs/              Detailed documentation
personas/          Ollama Modelfiles (JD Master)
scripts/           Evidence capture + helper scripts
rag/               Placeholders for datasets + ingestion
```

---

## License

Add one before publishing (MIT or Apache-2.0 are common).
