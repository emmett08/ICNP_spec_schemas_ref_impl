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

## Demo communication flow

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant P as Planner
    participant W as Writer
    participant R as Reviewer
    participant S as Summariser

    O->>O: Intent declaration (broadcast)
    P-->>O: Capability disclosure (compose_outline)
    W-->>O: Capability disclosure (write_draft)
    R-->>O: Capability disclosure (review_text)
    S-->>O: Capability disclosure (summarise_text)

    O->>O: Contract proposal (broadcast)
    P-->>O: Contract acceptance
    W-->>O: Contract acceptance
    R-->>O: Contract acceptance
    S-->>O: Contract acceptance

    O->>O: Execution token issuance (broadcast)

    O->>P: Execution request (compose_outline)
    P-->>O: Execution result + audit event

    O->>W: Execution request (write_draft)
    W-->>O: Execution result + audit event

    O->>R: Execution request (review_text)
    R-->>O: Execution result + audit event

    O->>S: Execution request (summarise_text)
    S-->>O: Execution result + audit event
```

---

## Prerequisites

1. **Ollama** installed and running locally:
   - Install (macOS): `brew install ollama`
   - Or download from https://ollama.com/download
   - Start the server (if it is not already running): `ollama serve`
   - Default API base URL: `http://localhost:11434`

2. Pull one or more models:
   - Llama 4 Scout: A 17 billion active parameter model featuring a massive
     10 million token context window, designed for handling huge documents and
     complex analysis.
     - `ollama pull llama4:scout`
   - Llama 4 Maverick: A 17 billion active parameter model that uses 128 experts
     in its MoE architecture, excelling in reasoning and coding tasks.
     - `ollama pull llama4:maverick`
   - Mistral 7B: A compact, general-purpose model that is fast to download and
     run locally.
     - `ollama pull mistral:7b`
   - Example alternative:
     - `ollama pull llama3.1:8b`
   - Expected download sizes (approx; from the Ollama model registry):
     - `llama3.1:8b`: ~4.9GB
     - `mistral:7b`: ~4.4GB
     - `llama4:scout`: ~67GB
     - `llama4:maverick`: ~245GB
    - Other quantizations and sizes:
      - https://ollama.com/library/llama3.1/tags
      - https://ollama.com/library/llama4/tags
      - https://ollama.com/library/mistral/tags

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

---

## Cleanup / Uninstall

Remove downloaded models:

```bash
ollama rm llama4:scout
ollama rm llama4:maverick
```

Uninstall Ollama:

- Homebrew: `brew uninstall ollama`
- macOS app: remove `Ollama.app` from `/Applications`
