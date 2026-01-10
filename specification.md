# ICNP — Inter-Component Negotiation Protocol
**Inferred reference specification (draft)**  
**Version:** 1.0.0-draft  
**Date:** 09 January 2026

---

## Table of contents

1. [Purpose](#purpose)  
2. [Scope and non-goals](#scope-and-non-goals)  
3. [Roles and responsibilities](#roles-and-responsibilities)  
4. [Core concepts](#core-concepts)  
5. [Protocol overview](#protocol-overview)  
6. [Message envelope](#message-envelope)  
7. [Phase 1 — Intent declaration](#phase-1--intent-declaration)  
8. [Phase 2 — Capability disclosure](#phase-2--capability-disclosure)  
9. [Phase 3 — Contract negotiation](#phase-3--contract-negotiation)  
10. [Phase 4 — Execution token](#phase-4--execution-token)  
11. [Governed execution](#governed-execution)  
12. [Audit events](#audit-events)  
13. [Error handling](#error-handling)  
14. [Idempotency, replay, and ordering](#idempotency-replay-and-ordering)  
15. [Security considerations](#security-considerations)  
16. [Versioning and extensibility](#versioning-and-extensibility)  
17. [Schemas and validation](#schemas-and-validation)  
18. [Worked example](#worked-example)

---

## Purpose

ICNP (Inter-Component Negotiation Protocol) is a **session-based negotiation protocol** for multi-agent and multi-component systems.

It defines how parties:

1. Declare **intent** (what is desired and under which constraints),
2. Disclose **capabilities** (what each party can do),
3. Negotiate an explicit **contract** (what is permitted/forbidden, with constraints and approvals),
4. Issue an **execution token** bound to that contract,
5. Perform **governed execution** with enforcement, audit, and violation handling.

ICNP’s aim is to make *authority explicit* and *execution verifiable*.

---

## Scope and non-goals

### In scope

- A **four-phase** handshake: Intent → Capability → Contract → Token
- Contract structure: permitted actions, forbidden actions, constraints, approvals
- Token structure: validity window, limits, and binding to the negotiated contract
- Governed execution requests/results and audit events
- Error codes and error message structure
- Guidance on replay/idempotency and correlation

### Out of scope (by design)

- The exact algorithm for capability matching, scoring, or constraint solving
- Real cryptographic primitives and key management (this spec defines fields and required properties, not an implementation)
- Transport details (HTTP, message buses, etc.) beyond ordering/replay guidance
- UI/UX conventions

---

## Roles and responsibilities

ICNP does not require fixed roles, but the following are typical:

- **Initiator**: starts a session by publishing an intent.
- **Responders**: disclose capabilities and participate in negotiation.
- **Orchestrator**: proposes a contract and coordinates acceptance (may be the initiator).
- **Issuer**: issues the execution token (often the orchestrator or a policy authority).
- **Enforcer**: validates tokens/contracts and enforces restrictions at execution time.
- **Auditor**: records audit events; may be collocated with enforcers.

A single process may play multiple roles.

---

## Core concepts

### Intent (intentional vs intensional)

ICNP uses "intent" in the intentional sense: a declaration of purpose and desired
outcome under constraints. It is not "intensional" in the logic/semantics sense
of describing meanings via context-dependent predicates or descriptions. In
short: "intent" here is about what you want to achieve, not how a term is
defined in a formal logic.

What intent refers to in ICNP (common scopes):

- Session/workflow intent: the `intent_declaration` payload (`intent.goal`,
  `intent.requested_actions`, and constraints). This is the normative intent for
  the session and is what negotiation binds to.
- Agent intent: a participant's internal goal or local policy. It may influence
  capability disclosure or contract negotiation, but it is not part of the
  protocol unless surfaced explicitly (e.g., in constraints or extensions).
- Contract intent: the explicit commitments encoded in the negotiated contract.
  Once accepted, this constrains execution regardless of individual agent intent.

If multiple kinds of intent must be expressed, keep them explicit and scoped
(e.g., in extensions or named constraint blocks) so that participants do not
conflate workflow intent with local agent goals.

### Session

A **session** represents one negotiation lifecycle.

- Identified by `session_id` (UUID).
- The session contains a **phase** and the artefacts produced in each phase:
  - intent
  - capabilities
  - contract
  - token
  - execution/audit records

### Capability

A capability describes what a party can do, with constraints.

- Identified by `capability_id` (UUID).
- Declares supported **actions** and **scopes**.
- May require approval, impose side-effect constraints, and carry a confidence score.

### Contract

A contract is the negotiated agreement that governs execution.

- Identified by `contract_id` (UUID).
- Enumerates:
  - **agreed actions** (what is authorised, by whom)
  - **forbidden actions** (explicit deny list)
  - **constraints** (risk, data handling, approvals, audit level, etc.)
  - **enforcement policy** (strict/permissive/audit-only and violation behaviour)
  - **approvals** (human or policy approvals)
  - **signatures** (participants sign the agreed contract)

### Execution token

A token is an attestation that a specific contract has been accepted and is in force.

- Identified by `token_id` (UUID).
- Binds to:
  - the session,
  - the contract,
  - and (optionally) hashes of relevant documents (intent/capabilities/contract).
- Contains:
  - validity window (`not_before`, `not_after`)
  - invocation limits
  - signature (issuer)

### Audit event

An audit event is an append-only record describing protocol or execution facts:

- contract acceptance
- token issuance
- execution started/completed
- violations/denials
- rollback actions

---

## Protocol overview

ICNP is a handshake with a governed execution stage:

```text
(Phase 1) Intent declaration
    Initiator -> Participants: INTENT_DECLARATION

(Phase 2) Capability disclosure
    Participant -> Orchestrator: CAPABILITY_DISCLOSURE

(Phase 3) Contract negotiation
    Orchestrator -> Participants: CONTRACT_PROPOSAL (or COUNTERPROPOSAL)
    Participant -> Orchestrator: CONTRACT_ACCEPTANCE / CONTRACT_REJECTION

(Phase 4) Execution token
    Issuer -> Participants/Enforcers: EXECUTION_TOKEN

Governed execution
    Orchestrator/Caller -> Executor: EXECUTION_REQUEST (token-bound)
    Executor -> Orchestrator/Caller: EXECUTION_RESULT (+ AUDIT_EVENT(s))
```

---

## Message envelope

All ICNP messages MUST use a common envelope.

### Envelope fields (normative)

- `icnp_version` (string): semantic version of ICNP (e.g. `"1.0.0"`).
- `type` (string): message type identifier.
- `phase` (string): protocol phase identifier.
- `message_id` (UUID): unique ID for this message.
- `session_id` (UUID): identifies the negotiation session.
- `timestamp` (RFC 3339 date-time): message creation time (UTC recommended).
- `sender` (object): sender identity.
- `recipient` (object, optional): recipient identity.
- `in_reply_to` (UUID, optional): message ID this message replies to.
- `trace` (object, optional): correlation/span identifiers.
- `payload` (object): message-specific payload.
- `extensions` (object, optional): extension point for forward compatibility.

### Sender/recipient identity

`sender` and `recipient` objects MUST include:

- `id` (string): stable identifier (agent/service name or UUID-like string).
- `role` (string): one of `orchestrator`, `agent`, `tool`, `service`, `user`.

Implementations SHOULD treat identity as an application concern (authentication/authorisation, keys, etc.), but the IDs MUST be stable for auditing.

---

## Phase 1 — Intent declaration

### Message type

- `type`: `intent_declaration`
- `phase`: `intent`

### Purpose

The initiator declares the goal and the constraints under which negotiation and execution may occur.

### Required payload fields

- `intent.goal` (string): concise goal.
- `intent.requested_actions` (array): requested action descriptors.
- `constraints` (object): risk tolerance, approvals, audit requirements, data policy, budgets.

### Intent constraints (recommended)

- `risk_tolerance`: `low | medium | high`
- `human_approval_required`: boolean
- `data_policy`: allowed data classes / retention requirements
- `external_side_effects_allowed`: boolean
- `audit_level`: `none | minimal | standard | full`

---

## Phase 2 — Capability disclosure

### Message type

- `type`: `capability_disclosure`
- `phase`: `capability`

### Purpose

Each participant discloses capabilities that may satisfy the intent.

### Required payload fields

- `capabilities` (array): one or more capabilities, each with:
  - `capability_id` (UUID)
  - `name` (string)
  - `actions` (array) each declaring:
    - `action` (string)
    - `scopes` (array of strings, optional)
    - `requires_approval` (boolean, optional)
    - `confidence` (number in `[0,1]`, optional)
    - `effects` (string, optional): `none|read|write|network|file|process`

### Notes

- Capabilities SHOULD be stable and reusable across sessions.
- A participant MAY disclose capabilities incrementally (multiple disclosure messages), but MUST maintain consistency for the session.

---

## Phase 3 — Contract negotiation

### Message types

- Proposal: `contract_proposal`
- Counterproposal: `contract_counterproposal`
- Acceptance: `contract_acceptance`
- Rejection: `contract_rejection`

All use:
- `phase`: `contract`

### Purpose

The orchestrator proposes a contract that:

- selects specific capabilities/actions,
- assigns executors,
- encodes constraints and enforcement,
- records approvals,
- collects signatures.

### Contract rules (normative)

- Every `agreed_action.capability_id` MUST reference a disclosed capability in the same session.
- A contract MUST include an `enforcement` policy.
- If `human_approval_required` is true (from intent or from any selected capability), the contract MUST include at least one approval record with decision `approve` before a token can be issued.
- Forbidden actions MUST dominate: if an action is in `forbidden_actions`, it MUST NOT be authorised even if accidentally listed in `agreed_actions`.

---

## Phase 4 — Execution token

### Message type

- `type`: `execution_token`
- `phase`: `token`

### Purpose

The issuer issues a token indicating the contract has been accepted and may be used for governed execution.

### Token rules (normative)

- `token.session_id` and `token.contract_id` MUST match the session and accepted contract.
- `not_before <= now < not_after` MUST hold for the token to be valid.
- Limits MUST be enforced. This spec defines two limits:
  - `limits.max_invocations_total` (requires shared state to enforce globally), and
  - `limits.max_invocations_per_actor` (enforceable locally).

Implementations MAY omit `max_invocations_total` if they do not provide shared state.

### Binding hashes

Tokens SHOULD contain binding hashes for tamper detection:

- `binding.intent_hash`
- `binding.contract_hash`
- `binding.capabilities_hash`

Hash computation and canonicalisation MUST be documented by the implementation. (The reference implementation includes a simple canonical JSON hash.)

---

## Governed execution

### Message types

- Request: `execution_request` (`phase`: `execution`)
- Result: `execution_result` (`phase`: `execution`)

### Execution request rules

An execution request MUST include:

- `invocation_id` (UUID)
- `token_id`, `contract_id`
- `action` (string)
- `executor.id` (string): which actor is expected to execute
- parameters (object)

The executor MUST:

1. Verify token validity (time window, signature, revocation if applicable),
2. Verify contract binding (contract id, session id),
3. Check that the requested action is permitted for that executor,
4. Enforce invocation limits,
5. Produce an `execution_result` and (if required) an `audit_event`.

### Violation behaviour

The executor MUST apply `enforcement.mode` and `violation_action` from the contract:

- **strict**: any violation -> deny or abort (and rollback if configured)
- **permissive**: allow certain violations but record them (implementation-defined)
- **audit_only**: do not block, but ALWAYS record violations

---

## Audit events

### Message type

- `type`: `audit_event`
- `phase`: `audit`

Audit events SHOULD be emitted for:

- contract acceptance
- token issuance
- execution start and completion
- denials/violations
- rollback actions

Audit events are append-only and SHOULD be durable.

---

## Error handling

### Message type

- `type`: `error`
- `phase`: `error`

### Error codes (baseline)

This inferred spec defines the following codes (you may extend):

- `ICNP-001` — invalid_intent
- `ICNP-002` — capability_mismatch
- `ICNP-003` — constraints_unsatisfiable
- `ICNP-004` — unauthorised_action
- `ICNP-005` — token_invalid
- `ICNP-006` — internal_error

Errors SHOULD include:

- `related_message_id` (if applicable),
- `retryable` boolean,
- `details` object for debugging.

---

## Idempotency, replay, and ordering

ICNP operates over asynchronous transports. Implementations SHOULD assume:

- messages may arrive out of order,
- messages may be duplicated,
- messages may be delayed.

### Requirements

- `message_id` MUST be globally unique per message.
- Recipients SHOULD implement a `seen` set per sender/session and ignore duplicates.
- `in_reply_to` MUST reference an existing message ID within the session to establish causality.
- Execution requests SHOULD include a `nonce` to mitigate replay. (Whether this is required depends on the threat model.)

---

## Security considerations

- **Identity and signatures:** The protocol assumes authenticated identities and signature verification. Implementations MUST define key distribution and trust.
- **Least privilege:** Contracts should authorise the minimum set of actions and scopes.
- **Expiry:** Tokens MUST be short-lived in high-risk contexts.
- **Audit integrity:** Audit logs should be append-only and tamper-evident.
- **Data policy:** Tokens and contracts SHOULD include data handling constraints where relevant.

---

## Versioning and extensibility

- `icnp_version` follows semantic versioning.
- `extensions` is an object reserved for implementation-specific fields.
- Implementations MUST ignore unknown fields in `extensions` and SHOULD preserve them when relaying messages.

---

## Schemas and validation

This bundle provides JSON Schema documents under `schemas/`.

- `schemas/common.schema.json` — shared definitions
- `schemas/envelope.schema.json` — base envelope
- `schemas/intent.schema.json` — intent message
- `schemas/capability.schema.json` — capability message
- `schemas/contract.schema.json` — contract negotiation messages
- `schemas/execution-token.schema.json` — execution token message
- `schemas/execution.schema.json` — execution request/result messages
- `schemas/audit.schema.json` — audit events
- `schemas/error.schema.json` — error messages

---

## Worked example

See `examples/` for a complete 5-agent conversation that follows:

- intent declaration
- capability disclosures
- contract proposal and acceptances
- token issuance
- execution requests and results
- audit events

The reference implementation under `reference-implementation/` reproduces the same flow using five Ollama-backed agents and prints every ICNP message exchanged.
