# ICNP Reference Implementation (5 Ollama agents)

This is a small, runnable reference implementation demonstrating **visible ICNP message exchange**
between **five Ollama-backed agents**:

- 1× Orchestrator
- 4× Specialist agents (Planner, Writer, Reviewer, Summariser)

It performs:

1. Intent declaration
2. Capability disclosure
3. Contract proposal and acceptance
4. Execution token issuance
5. Governed execution requests/results (+ audit events)

Every ICNP message is printed to the console as formatted JSON.

---

## Prerequisites

1. **Ollama** installed and running locally:
   - Default API base URL: `http://localhost:11434`

2. At least one model pulled, for example:
   - `ollama pull llama3.1:8b`

3. Python 3.10+ recommended

---

## Install

```bash
cd reference-implementation
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Run

```bash
python demo_ollama_5_agents.py --model llama3.1:8b
```

Optional:

- Use different models per agent:
  ```bash
  python demo_ollama_5_agents.py \
    --model-orchestrator llama3.1:8b \
    --model-planner llama3.1:8b \
    --model-writer mistral:7b \
    --model-reviewer llama3.1:8b \
    --model-summariser llama3.1:8b
  ```

- Dry-run (no Ollama calls; returns canned outputs):
  ```bash
  python demo_ollama_5_agents.py --dry-run
  ```

---

## Notes

- This demo uses **HMAC-SHA256** signatures purely as a lightweight example.
- In a real system you would likely use asymmetric signatures (e.g. Ed25519) and proper key distribution.
- The message structures match the schemas in `../schemas/`.
