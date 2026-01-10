# ICNP Capability Vocabulary

## Overview

The Capability Vocabulary defines standardized terms for expressing what a service, agent, or component can and cannot do.

## Action Taxonomy

### Primary Actions

| Action     | Description                          | Side Effects | Reversible |
| ---------- | ------------------------------------ | ------------ | ---------- |
| `read`     | Retrieve data without modification   | None         | N/A        |
| `write`    | Create or update data                | Yes          | Maybe      |
| `delete`   | Remove data                          | Yes          | Maybe      |
| `execute`  | Run a process or command             | Yes          | Maybe      |
| `simulate` | Model execution without side effects | None         | N/A        |
| `suggest`  | Propose without executing            | None         | N/A        |
| `decide`   | Make autonomous decisions            | Yes          | No         |
| `delegate` | Pass control to another party        | Yes          | Maybe      |

### Compound Actions

| Action        | Composed Of            | Use Case            |
| ------------- | ---------------------- | ------------------- |
| `read-write`  | read + write           | CRUD operations     |
| `analyze`     | read + simulate        | Data analysis       |
| `transform`   | read + write + execute | Data processing     |
| `orchestrate` | execute + delegate     | Workflow management |
| `audit`       | read + analyze         | Compliance checking |

## Scope Taxonomy

### Resource Scopes

| Scope           | Description              | Examples                 |
| --------------- | ------------------------ | ------------------------ |
| `repository`    | Source code repositories | GitHub, GitLab           |
| `database`      | Data storage             | PostgreSQL, MongoDB      |
| `configuration` | System settings          | K8s ConfigMaps, env vars |
| `secrets`       | Sensitive credentials    | Vault, AWS Secrets       |
| `deployment`    | Deployment resources     | K8s, Docker, VMs         |
| `network`       | Network resources        | DNS, Load balancers      |
| `monitoring`    | Observability systems    | Prometheus, Grafana      |

### Data Scopes

| Scope               | Description           | Sensitivity |
| ------------------- | --------------------- | ----------- |
| `public_data`       | Publicly available    | Low         |
| `internal_data`     | Organization internal | Medium      |
| `confidential_data` | Business sensitive    | High        |
| `pii_data`          | Personal identifiable | Critical    |
| `phi_data`          | Protected health      | Critical    |
| `financial_data`    | Financial records     | Critical    |

### Environment Scopes

| Scope               | Description      | Risk Level |
| ------------------- | ---------------- | ---------- |
| `development`       | Dev environment  | Low        |
| `testing`           | Test environment | Low        |
| `staging`           | Pre-production   | Medium     |
| `production`        | Live systems     | High       |
| `disaster_recovery` | DR environment   | High       |

## Capability Schema

```typescript
interface Capability {
  id: string;
  action: Action;
  scope: Scope | Scope[];

  // Confidence in ability to perform (0.0 - 1.0)
  confidence: number;

  // Whether human approval is needed
  requires_approval: boolean;

  // Expected side effects
  side_effects: "none" | "minimal" | "moderate" | "significant";

  // Prerequisites
  prerequisites?: string[];

  // Resource requirements
  resource_requirements?: {
    cpu_cores?: number;
    memory_gb?: number;
    duration_seconds?: number;
  };

  // Certifications/compliance
  certifications?: string[];
}
```

## Limitation Schema

```typescript
interface Limitation {
  id: string;
  action: Action;
  scope: Scope | Scope[];

  // Why this limitation exists
  reason?: string;

  // Whether this is absolute or conditional
  type: "absolute" | "conditional";

  // Conditions under which limitation applies
  conditions?: Record<string, unknown>;
}
```

## Examples

### Capability Example

```json
{
  "id": "deploy-simulate",
  "action": "simulate",
  "scope": ["deployment", "configuration"],
  "confidence": 0.92,
  "requires_approval": false,
  "side_effects": "none",
  "prerequisites": ["repo-read"],
  "resource_requirements": {
    "cpu_cores": 2,
    "memory_gb": 4,
    "duration_seconds": 300
  },
  "certifications": ["SOC2"]
}
```

### Limitation Example

```json
{
  "id": "no-prod-write",
  "action": "write",
  "scope": "production",
  "reason": "Safety policy - requires human approval",
  "type": "conditional",
  "conditions": {
    "unless": "human_approval_granted"
  }
}
```

## Confidence Scoring

| Score     | Meaning              | Recommended Use       |
| --------- | -------------------- | --------------------- |
| 0.95+     | Very high confidence | Autonomous execution  |
| 0.80-0.94 | High confidence      | Supervised execution  |
| 0.60-0.79 | Medium confidence    | Human review required |
| 0.40-0.59 | Low confidence       | Simulation only       |
| <0.40     | Very low confidence  | Not recommended       |
