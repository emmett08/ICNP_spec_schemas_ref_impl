# ICNP - Intent-and-Capability Negotiation Protocol

This repository contains:

- `icnp/`: canonical ICNP docs (specification, schemas, examples, guides).
- `specification.md`: ICNP protocol specification (mirrors `icnp/specification.md`).
- `schemas/`: JSON Schemas for ICNP messages (mirrors `icnp/schemas/`).
- `examples/`: example ICNP message bundles (mirrors `icnp/examples/`).
- `reference-implementation/`: a runnable demo with 5 Ollama-backed agents.

## Bull with yoke

<svg width="360" height="180" viewBox="0 0 360 180" role="img" aria-label="Bull with yoke" xmlns="http://www.w3.org/2000/svg">
  <rect width="360" height="180" fill="none"/>
  <ellipse cx="210" cy="95" rx="95" ry="45" fill="#5a3b2e"/>
  <circle cx="120" cy="95" r="28" fill="#5a3b2e"/>
  <ellipse cx="110" cy="105" rx="10" ry="12" fill="#3b261e"/>
  <ellipse cx="130" cy="105" rx="10" ry="12" fill="#3b261e"/>
  <path d="M 95 75 C 75 55, 45 55, 30 75" fill="none" stroke="#3b261e" stroke-width="6" stroke-linecap="round"/>
  <path d="M 145 75 C 165 55, 195 55, 210 75" fill="none" stroke="#3b261e" stroke-width="6" stroke-linecap="round"/>
  <rect x="135" y="70" width="140" height="22" rx="10" fill="#d6a15a" stroke="#8a5b2b" stroke-width="3"/>
  <rect x="185" y="88" width="40" height="22" rx="8" fill="#d6a15a" stroke="#8a5b2b" stroke-width="3"/>
  <circle cx="150" cy="81" r="4" fill="#8a5b2b"/>
  <circle cx="260" cy="81" r="4" fill="#8a5b2b"/>
  <rect x="175" y="125" width="16" height="35" rx="4" fill="#5a3b2e"/>
  <rect x="205" y="125" width="16" height="35" rx="4" fill="#5a3b2e"/>
  <rect x="235" y="125" width="16" height="35" rx="4" fill="#5a3b2e"/>
  <rect x="265" y="125" width="16" height="35" rx="4" fill="#5a3b2e"/>
  <circle cx="110" cy="90" r="4" fill="#1c1b1a"/>
  <circle cx="130" cy="90" r="4" fill="#1c1b1a"/>
  <path d="M 113 102 Q 120 108 127 102" fill="none" stroke="#1c1b1a" stroke-width="3" stroke-linecap="round"/>
</svg>

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
