
# Local AI Cybersecurity RAG Lab

## Overview
This project documents the design and implementation of a **local, offline-first AI system** built to support cybersecurity learning and analysis.  
The goal is not to replace enterprise SOC tooling, but to **understand how knowledge grounding, attack frameworks, and pipelines interact in practice**.

The system combines:
- Local LLMs (via Ollama)
- Retrieval-Augmented Generation (RAG)
- Curated security knowledge bases (Wikipedia, MITRE ATT&CK)
- A pipeline-oriented design approach

---

## Why this project
Most AI or SOC labs focus on tools in isolation.  
This project focuses on **how systems are designed, integrated, and reasoned about**.

Key objectives:
- Reduce hallucinations through grounding
- Learn attacker-centric frameworks (MITRE ATT&CK)
- Practice building reproducible data pipelines
- Explore how AI can assist, not replace, SOC workflows

---

## High-level architecture
