# ICNP Spec, Schemas, and Reference Implementation

This repository contains:

- `specification.md`: the ICNP specification.
- `schemas/`: JSON Schemas for ICNP message types.
- `examples/`: example ICNP messages matching the schemas.
- `reference-implementation/`: a runnable demo with 5 Ollama-backed agents.

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

See `reference-implementation/README.md` for full usage and options.
