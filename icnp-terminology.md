# ICNP Terminology Note

This note clarifies a common confusion:

- "Intent" in ICNP is **intentional** (purpose or desired outcome).
- It is **not** "intensional" in the logic/semantics sense (meaning defined by a
  predicate or context).

In practice:

- **Workflow intent** is the protocol-level declaration (the `intent` object in
  `intent_declaration`).
- **Agent intent** is a participant's internal goal or policy and is only part
  of ICNP if explicitly surfaced.
- **Contract intent** is the agreed commitment encoded in the negotiated
  contract and enforced by the execution token.
