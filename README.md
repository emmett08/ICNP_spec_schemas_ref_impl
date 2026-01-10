# ICNP - Intent-and-Capability Negotiation Protocol

This repository contains:

- `icnp/`: canonical ICNP docs (specification, schemas, examples, guides).
- `specification.md`: ICNP protocol specification (mirrors `icnp/specification.md`).
- `schemas/`: JSON Schemas for ICNP messages (mirrors `icnp/schemas/`).
- `examples/`: example ICNP message bundles (mirrors `icnp/examples/`).
- `reference-implementation/`: a runnable demo with 5 Ollama-backed agents.

Illustration of agents with power constrained by ICNP.

<img src="assets/bull-yoke.svg" width="360" alt="Bull with a yoke representing constrained power" />

## Overview

ICNP (Intent-and-Capability Negotiation Protocol) is a first-class, machine-readable
protocol for expressing intent, negotiating capabilities, and enforcing contracts
between components, services, agents, and humans-in-the-loop **before** any data
exchange or API call happens.

It defines a clear handshake:

1. Intent declaration
2. Capability disclosure
3. Contract negotiation
4. Execution token issuance

### What gap it fills

Modern systems often rely on implicit assumptions about authority and side
effects. ICNP makes those assumptions explicit by standardizing:

- What is being asked for (intent)
- What each participant can do (capability)
- What is permitted or forbidden (contract)
- Who is authorized, for how long, and under what limits (token)

### Why it is needed

Without a shared negotiation protocol, systems are harder to audit, constrain,
and compose safely. ICNP provides a concrete, verifiable trail from goals to
execution, enabling consistent enforcement and easier integration across
heterogeneous agents, tools, and services.

For the canonical protocol documentation, start with `icnp/README.md`.
For a short terminology clarification, see `icnp-terminology.md`.

## Quick start (demo)

```bash
# Optional: if you use pyenv
pyenv install 3.14.2
pyenv local 3.14.2
```

If `python --version` still shows 3.9.x after `pyenv local`, initialize pyenv in
your shell (one-time setup) or run this in the current shell:

```bash
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```

Then create the venv and install the demo:

```bash
python --version  # should be 3.10+
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -e reference-implementation
python reference-implementation/demo_ollama_5_agents.py --model llama3.1:8b
```

If you see `requires a different Python: 3.9.6 not in '>=3.10'`, delete the
`.venv` and recreate it after setting `pyenv local` and confirming
`python --version` is 3.10+.

Animated intent graph (GitHub Pages):

```
https://emmett08.github.io/ICNP_spec_schemas_ref_impl/reference-implementation/demo_graph_intent_flow.html
```

See `reference-implementation/README.md` for full usage and options.
