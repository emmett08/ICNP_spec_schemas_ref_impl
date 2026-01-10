# ICNP Use Cases

This document provides detailed use cases for implementing the Intent-and-Capability Negotiation Protocol (ICNP) across different scenarios.

## Use Case 1: Multi-Agent Workflow Communication

ICNP provides a formal protocol for agents to negotiate capabilities and establish contracts **before** exchanging workflow data.

### The Problem

In multi-agent workflows, agents must:

- Know what other agents can do
- Agree on data formats and constraints
- Handle capability mismatches gracefully
- Maintain audit trails of all interactions

### ICNP Solution

Each agent-to-agent communication follows the 4-phase ICNP handshake:

```text
┌─────────────────┐                      ┌─────────────────┐
│   Agent A       │                      │   Agent B       │
│   (Requester)   │                      │   (Provider)    │
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         │  1. Intent Declaration                 │
         │  "I need code review with security    │
         │   focus, output in SARIF format"      │
         │───────────────────────────────────────▶│
         │                                        │
         │  2. Capability Disclosure              │
         │  "I can: analyze, suggest, report     │
         │   I cannot: modify, deploy"           │
         │◀───────────────────────────────────────│
         │                                        │
         │  3. Contract Negotiation               │
         │  "Agreed: analyze + report             │
         │   Forbidden: write access"            │
         │◀──────────────────────────────────────▶│
         │                                        │
         │  4. Execution Token                    │
         │  "Here's your signed token,           │
         │   valid for 300 seconds"              │
         │◀───────────────────────────────────────│
         │                                        │
         │  === Actual Work Begins ===            │
         │  (All actions validated against token) │
         │◀──────────────────────────────────────▶│
```

### Workflow Integration Example

```yaml
# ICNP-enabled workflow step
steps:
  - name: "security_review"
    agent: "hestia"
    icnp:
      intent:
        action: "security-analysis"
        goals:
          - id: "find-vulnerabilities"
            priority: "critical"
          - id: "compliance-check"
            priority: "high"
            standard: "OWASP-Top-10"
        constraints:
          max_duration_seconds: 300
          output_format: "SARIF"
      required_capabilities:
        - action: "analyze"
          scope: "source-code"
      forbidden_actions:
        - action: "write"
          scope: "any"
        - action: "network"
          scope: "external"
    inputs:
      code_path: "{{steps.checkout.output.path}}"
    outputs:
      - security_report
      - vulnerability_list
```

### Benefits for Workflows

| Aspect                 | Without ICNP             | With ICNP                |
| ---------------------- | ------------------------ | ------------------------ |
| Capability discovery   | Hard-coded agent configs | Dynamic negotiation      |
| Error handling         | Runtime failures         | Pre-execution validation |
| Audit trail            | Log parsing              | Structured contracts     |
| Trust verification     | Implicit trust           | Cryptographic binding    |
| Constraint enforcement | Hope for the best        | Token-enforced limits    |

---

## Use Case 2: CI/CD Pipeline Orchestration

### Scenario

A deployment pipeline where each stage must negotiate:

- Resource access (repos, registries, clusters)
- Permissions (read, write, deploy)
- Constraints (time windows, approval requirements)

### ICNP Flow

```yaml
# CI/CD with ICNP negotiations
pipeline:
  stages:
    - name: "build"
      icnp:
        intent:
          action: "compile-artifacts"
          goals:
            - id: "produce-container"
              output: "container-image"
          constraints:
            cost: { max: 10, currency: "USD" }
            time: { max_minutes: 15 }

    - name: "deploy-staging"
      icnp:
        intent:
          action: "deploy"
          goals:
            - id: "successful-deployment"
              environment: "staging"
          non_goals:
            - id: "no-production-access"
        required_approvals:
          - role: "developer"

    - name: "deploy-production"
      icnp:
        intent:
          action: "deploy"
          goals:
            - id: "successful-deployment"
              environment: "production"
          constraints:
            time_window: { start: "02:00", end: "06:00", tz: "UTC" }
        required_approvals:
          - role: "sre"
          - role: "security"
```

---

## Use Case 3: Cross-Organization API Integration

### Scenario 1

Two organizations integrating services where:

- Neither fully trusts the other
- Data residency requirements apply
- Costs must be tracked and limited

### ICNP Contract Example

```json
{
  "icnp_version": "1.0",
  "phase": "contract_negotiation",
  "parties": {
    "initiator": { "org": "acme-corp", "service": "order-service" },
    "responder": { "org": "partner-inc", "service": "fulfillment-api" }
  },
  "agreed_actions": [
    { "action": "create", "scope": "orders", "rate_limit": "100/hour" },
    { "action": "read", "scope": "order_status" },
    { "action": "read", "scope": "tracking_info" }
  ],
  "forbidden_actions": [
    { "action": "read", "scope": "customer_pii" },
    { "action": "delete", "scope": "any" }
  ],
  "constraints": {
    "data_residency": ["US", "EU"],
    "encryption": "TLS1.3+",
    "audit_retention_days": 365
  },
  "sla": {
    "availability": "99.9%",
    "latency_p99_ms": 200
  }
}
```

---

## Use Case 4: AI Agent Tool Access

### Scenario 2

An AI agent needs to access external tools (web search, code execution, file system) with strict safety constraints.

### ICNP Safety Boundaries

```json
{
  "intent": {
    "action": "research-topic",
    "goals": [{ "id": "gather-information", "topic": "{{user_query}}" }],
    "constraints": {
      "no_code_execution": true,
      "no_file_writes": true,
      "allowed_domains": ["*.wikipedia.org", "*.arxiv.org"],
      "max_requests": 10
    },
    "risk_tolerance": "low"
  },
  "capabilities_requested": [
    { "action": "read", "scope": "web", "purpose": "research" }
  ],
  "human_approval_required": false
}
```

---

## Use Case 5: Regulated Healthcare Workflows

### Scenario 3

Medical data processing with HIPAA compliance requirements.

### ICNP Compliance Enforcement

```yaml
workflow:
  name: "patient-data-analysis"
  icnp:
    global_constraints:
      compliance: ["HIPAA", "GDPR"]
      data_classification: "PHI"
      encryption:
        at_rest: "AES-256"
        in_transit: "TLS1.3"
      audit:
        level: "full"
        retention_years: 7
      access_control:
        requires_role: "healthcare-provider"
        requires_training: "HIPAA-certified"

  steps:
    - name: "analyze_records"
      agent: "medical-ai"
      icnp:
        intent:
          action: "analyze-patient-data"
          goals:
            - id: "risk-assessment"
              output: "risk_score"
          non_goals:
            - id: "no-data-export"
            - id: "no-patient-identification"
        forbidden_actions:
          - action: "export"
            scope: "any"
          - action: "identify"
            scope: "patient"
        minimum_confidence: 0.95
```

---

## Use Case 6: Edge Computing Resource Negotiation

### Scenario 4

Edge nodes negotiating compute resources with limited bandwidth.

### ICNP Lightweight Negotiation

```json
{
  "icnp_version": "1.0",
  "mode": "edge-optimized",
  "intent": {
    "action": "process-sensor-data",
    "constraints": {
      "compute": { "cpu_millicores": 500, "memory_mb": 256 },
      "network": { "bandwidth_kbps": 100, "latency_ms": 50 },
      "power": { "max_watts": 5 }
    },
    "deadline_ms": 1000
  },
  "fallback": {
    "on_constraint_violation": "degrade-quality",
    "minimum_acceptable": {
      "compute": { "cpu_millicores": 100 }
    }
  }
}
```

---

## Use Case 7: Financial Trading Compliance

### Scenario 5

Algorithmic trading with regulatory constraints.

### ICNP Pre-Trade Validation

```json
{
  "intent": {
    "action": "execute-trade",
    "goals": [{ "id": "fill-order", "instrument": "AAPL", "quantity": 1000 }],
    "constraints": {
      "regulations": ["MiFID-II", "SEC-Rule-15c3-5"],
      "risk_limits": {
        "max_notional_usd": 1000000,
        "max_position_pct": 5
      },
      "pre_trade_checks": ["fat-finger", "position-limit", "credit-check"],
      "execution_venue": ["NYSE", "NASDAQ"]
    }
  },
  "required_approvals": [],
  "auto_reject_on": ["risk_limit_exceeded", "regulation_violation"]
}
```

---

## Use Case 8: Multi-Cloud Orchestration

### Scenario 6

Workloads spanning AWS, GCP, and Azure with cost optimization.

### ICNP Cloud Negotiation

```yaml
intent:
  action: "deploy-workload"
  goals:
    - id: "high-availability"
      regions: ["us-east", "eu-west", "ap-southeast"]
    - id: "cost-optimization"
      max_monthly_usd: 5000

  preferences:
    cloud_preference:
      - provider: "gcp"
        weight: 0.4
        reason: "existing-credits"
      - provider: "aws"
        weight: 0.35
      - provider: "azure"
        weight: 0.25

  constraints:
    data_residency:
      eu_data: ["eu-west"]
      us_data: ["us-east", "us-west"]
    security:
      encryption: "customer-managed-keys"
      network: "private-only"
```

---

## Use Case 9: Autonomous Vehicle Coordination

### Scenario 7

Vehicle-to-vehicle (V2V) negotiation for lane changes, merging.

### ICNP Real-Time Negotiation

```json
{
  "icnp_version": "1.0",
  "mode": "real-time",
  "max_negotiation_ms": 50,
  "intent": {
    "action": "lane-change",
    "goals": [{ "id": "merge-left", "urgency": "normal" }],
    "constraints": {
      "safety_distance_m": 3,
      "max_deceleration_ms2": 3
    }
  },
  "capability_disclosure": {
    "current_speed_ms": 25,
    "position": { "lane": 2, "distance_ahead_m": 50 },
    "can_yield": true,
    "yield_cost": "low"
  }
}
```

---

## Use Case 10: Smart Contract Pre-Negotiation

### Scenario 8

Off-chain negotiation before on-chain smart contract execution.

### ICNP to Smart Contract Bridge

```json
{
  "intent": {
    "action": "execute-swap",
    "goals": [
      { "id": "token-swap", "from": "ETH", "to": "USDC", "amount": 1.5 }
    ],
    "constraints": {
      "min_output": 2800,
      "max_slippage_pct": 0.5,
      "deadline_block": 18500000,
      "gas_limit_gwei": 100
    }
  },
  "on_agreement": {
    "generate": "smart-contract-call",
    "chain": "ethereum",
    "contract": "0x..."
  }
}
```

---

## Summary

ICNP provides a universal negotiation layer for:

| Domain             | Key Benefit                        |
| ------------------ | ---------------------------------- |
| Workflow Agents    | Pre-execution capability matching  |
| CI/CD Pipelines    | Stage-level permission negotiation |
| Cross-Org APIs     | Trust boundaries with SLAs         |
| AI Tool Access     | Safety constraints enforcement     |
| Healthcare         | Compliance-first data handling     |
| Edge Computing     | Resource-constrained negotiation   |
| Financial Trading  | Pre-trade regulatory checks        |
| Multi-Cloud        | Cost and residency optimization    |
| Autonomous Systems | Real-time coordination             |
| Blockchain         | Off-chain pre-negotiation          |

## Related Documents

- [Protocol Specification](./specification.md)
- [Implementation Guide](./implementation-guide.md)
- [Capability Vocabulary](./capability-vocabulary.md)
- [Intent Schema](./intent-schema.md)
