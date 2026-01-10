# ICNP Intent Schema

## Overview

The Intent Schema defines the structure for expressing what a party wants to achieve, including goals, non-goals, constraints, and risk tolerance.

## Schema Definition

```typescript
interface Intent {
  // What the initiator wants to accomplish
  action: string;

  // Prioritized list of goals
  goals: Goal[];

  // Explicit non-goals (things to avoid)
  non_goals: NonGoal[];

  // Hard and soft constraints
  constraints: Constraints;

  // Risk appetite
  risk_tolerance: "none" | "low" | "medium" | "high";

  // Whether human approval is required
  human_approval_required: boolean;

  // Context for better understanding
  context?: IntentContext;
}

interface Goal {
  id: string;
  description?: string;
  priority: "critical" | "high" | "medium" | "low";
  metric?: string; // Measurable success criteria
  standard?: string; // Compliance standard if applicable
}

interface NonGoal {
  id: string;
  description?: string;
  reason: string; // Why this is excluded
  severity: "hard" | "soft"; // Hard = absolute, Soft = preferably avoid
}

interface Constraints {
  // Cost constraints
  cost?: {
    max: number;
    currency: string;
    period: "hour" | "day" | "month" | "total";
  };

  // Performance constraints
  latency?: {
    max_ms: number;
    percentile: number;
  };

  // Geographic constraints
  data_residency?: string[];

  // Time constraints
  time_window?: {
    start: string; // HH:MM
    end: string; // HH:MM
    timezone: string;
    days?: string[]; // ['monday', 'tuesday', ...]
  };

  // Resource constraints
  resources?: {
    max_cpu_cores?: number;
    max_memory_gb?: number;
    max_storage_gb?: number;
    max_network_mbps?: number;
  };

  // Custom constraints
  custom?: Record<string, unknown>;
}

interface IntentContext {
  // Previous related intents
  related_intents?: string[];

  // Business context
  business_unit?: string;
  project?: string;
  environment?: "development" | "staging" | "production";

  // Urgency
  urgency?: "immediate" | "soon" | "scheduled" | "background";
}
```

## Examples

### Example 1: Deployment Optimization

```json
{
  "action": "optimize-deployment-pipeline",
  "goals": [
    { "id": "reduce-mttr", "priority": "high", "metric": "MTTR < 15min" },
    { "id": "maintain-compliance", "priority": "critical", "standard": "SOC2" }
  ],
  "non_goals": [
    {
      "id": "no-prod-changes",
      "reason": "safety constraint",
      "severity": "hard"
    }
  ],
  "constraints": {
    "cost": { "max": 50, "currency": "GBP", "period": "month" },
    "latency": { "max_ms": 200, "percentile": 99 }
  },
  "risk_tolerance": "low",
  "human_approval_required": true
}
```

### Example 2: Data Analysis

```json
{
  "action": "analyze-customer-segments",
  "goals": [
    {
      "id": "identify-churn-risk",
      "priority": "high",
      "metric": "precision > 0.85"
    },
    { "id": "generate-insights", "priority": "medium" }
  ],
  "non_goals": [
    { "id": "no-pii-export", "reason": "GDPR compliance", "severity": "hard" },
    {
      "id": "no-real-time",
      "reason": "batch is sufficient",
      "severity": "soft"
    }
  ],
  "constraints": {
    "data_residency": ["EU"],
    "time_window": { "start": "00:00", "end": "06:00", "timezone": "UTC" }
  },
  "risk_tolerance": "medium",
  "human_approval_required": false,
  "context": {
    "business_unit": "marketing",
    "environment": "production",
    "urgency": "scheduled"
  }
}
```

### Example 3: Agent Tool Access

```json
{
  "action": "execute-code-review",
  "goals": [
    { "id": "find-bugs", "priority": "high" },
    { "id": "check-security", "priority": "critical" },
    { "id": "suggest-improvements", "priority": "medium" }
  ],
  "non_goals": [
    {
      "id": "no-auto-commit",
      "reason": "human review required",
      "severity": "hard"
    },
    {
      "id": "no-external-calls",
      "reason": "air-gapped environment",
      "severity": "hard"
    }
  ],
  "constraints": {
    "resources": { "max_cpu_cores": 4, "max_memory_gb": 8 }
  },
  "risk_tolerance": "none",
  "human_approval_required": true
}
```

## Validation Rules

1. At least one goal must have priority "critical" or "high"
2. All non-goals with severity "hard" must be enforceable
3. Constraints must be non-conflicting
4. risk_tolerance "none" requires human_approval_required = true
