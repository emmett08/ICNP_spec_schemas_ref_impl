# ICNP Protocol Specification

## Version 1.0

## Protocol Phases

### Phase 1: Intent Declaration

The initiating party declares their intent using the Intent Schema.

```json
{
  "icnp_version": "1.0",
  "phase": "intent_declaration",
  "message_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "intent": {
    "action": "optimise-deployment-pipeline",
    "goals": [
      { "id": "reduce-mttr", "priority": "high", "metric": "MTTR < 15min" },
      {
        "id": "maintain-compliance",
        "priority": "critical",
        "standard": "SOC2"
      }
    ],
    "non_goals": [{ "id": "no-prod-changes", "reason": "safety constraint" }],
    "constraints": {
      "cost": { "max": 50, "currency": "GBP", "period": "month" },
      "latency": { "max_ms": 200, "percentile": 99 },
      "data_residency": ["UK", "EU"],
      "time_window": { "start": "02:00", "end": "06:00", "timezone": "UTC" }
    },
    "risk_tolerance": "low",
    "human_approval_required": true
  },
  "sender": {
    "id": "agent-orchestrator-001",
    "type": "autonomous-agent",
    "trust_level": "verified"
  }
}
```

### Phase 2: Capability Disclosure

The receiving party discloses their capabilities and limitations.

```json
{
  "icnp_version": "1.0",
  "phase": "capability_disclosure",
  "in_reply_to": "uuid-from-phase-1",
  "capabilities": [
    {
      "id": "repo-read",
      "action": "read",
      "scope": "repository",
      "confidence": 0.99
    },
    {
      "id": "deploy-simulate",
      "action": "simulate",
      "scope": "deployment",
      "confidence": 0.87,
      "requires_approval": false
    },
    {
      "id": "config-suggest",
      "action": "suggest",
      "scope": "configuration",
      "confidence": 0.82,
      "side_effects": "none"
    }
  ],
  "limitations": [
    { "id": "no-prod-write", "action": "write", "scope": "production" },
    { "id": "no-pii", "action": "access", "scope": "pii_data" }
  ],
  "resource_requirements": {
    "compute": { "cpu_cores": 2, "memory_gb": 4 },
    "estimated_duration_seconds": 300
  },
  "responder": {
    "id": "deployment-optimizer-agent",
    "version": "2.1.0",
    "certifications": ["SOC2", "ISO27001"]
  }
}
```

### Phase 3: Contract Negotiation

Both parties negotiate and agree on the execution contract.

```json
{
  "icnp_version": "1.0",
  "phase": "contract_negotiation",
  "contract_id": "uuid-v4",
  "agreed_actions": [
    { "capability_id": "repo-read", "approved": true },
    { "capability_id": "deploy-simulate", "approved": true },
    { "capability_id": "config-suggest", "approved": true }
  ],
  "forbidden_actions": [
    { "action": "write", "scope": "production", "reason": "non-goal" },
    { "action": "delete", "scope": "any", "reason": "safety" }
  ],
  "execution_constraints": {
    "audit_level": "full",
    "logging_required": true,
    "rollback_required": true,
    "max_duration_seconds": 600,
    "checkpoint_interval_seconds": 60
  },
  "approval_chain": [
    { "approver": "human-operator", "approved_at": "ISO-8601" }
  ],
  "signatures": {
    "initiator": "base64-signature",
    "responder": "base64-signature"
  }
}
```

### Phase 4: Execution Token

A cryptographically bound token governs runtime behavior.

```json
{
  "icnp_version": "1.0",
  "phase": "execution_token",
  "token_id": "uuid-v4",
  "contract_id": "reference-to-phase-3",
  "token": "jwt-or-similar",
  "validity": {
    "not_before": "ISO-8601",
    "not_after": "ISO-8601",
    "max_invocations": 1
  },
  "binding": {
    "intent_hash": "sha256-of-intent",
    "contract_hash": "sha256-of-contract",
    "capability_hashes": ["sha256-of-each-capability"]
  },
  "enforcement": {
    "mode": "strict",
    "violation_action": "abort_and_rollback",
    "alert_on_violation": true
  }
}
```

## Message Flow

```text
┌──────────┐                              ┌──────────┐
│ Initiator│                              │ Responder│
└────┬─────┘                              └────┬─────┘
     │                                         │
     │──── Intent Declaration ────────────────>│
     │                                         │
     │<─── Capability Disclosure ──────────────│
     │                                         │
     │──── Contract Proposal ─────────────────>│
     │                                         │
     │<─── Contract Counter/Accept ────────────│
     │                                         │
     │──── Contract Signature ────────────────>│
     │                                         │
     │<─── Execution Token ────────────────────│
     │                                         │
     │==== Governed Execution =================>│
     │                                         │
     │<─── Execution Result + Audit ───────────│
     │                                         │
```

## Error Handling

| Error Code | Meaning                  | Action             |
| ---------- | ------------------------ | ------------------ |
| ICNP-001   | Intent not understood    | Clarify intent     |
| ICNP-002   | No matching capabilities | Abort or fallback  |
| ICNP-003   | Constraint conflict      | Negotiate or abort |
| ICNP-004   | Contract rejected        | Review and retry   |
| ICNP-005   | Token expired            | Re-negotiate       |
| ICNP-006   | Execution violation      | Rollback + alert   |
