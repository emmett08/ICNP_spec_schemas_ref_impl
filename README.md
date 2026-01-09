# ICNP Spec, Schemas, and Reference Implementation

This repository contains:

- `specification.md`: the ICNP specification.
- `schemas/`: JSON Schemas for ICNP message types.
- `examples/`: example ICNP messages matching the schemas.
- `reference-implementation/`: a runnable demo with 5 Ollama-backed agents.

## Quick start (demo)

```bash
cd reference-implementation
python -m venv .venv
source .venv/bin/activate
pip install -e .
python demo_ollama_5_agents.py --model llama3.1:8b
```

See `reference-implementation/README.md` for full usage and options.
