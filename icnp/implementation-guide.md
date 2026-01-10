# ICNP Implementation Guide

## Overview

This guide walks through implementing the Intent-and-Capability Negotiation Protocol from design to deployment.

## Architecture Components

### 1. Intent Engine

Responsible for parsing, validating, and managing intent declarations.

```typescript
interface IntentEngine {
  // Parse and validate an intent declaration
  parseIntent(raw: unknown): Result<Intent, ValidationError[]>;

  // Check if intent is achievable given known capabilities
  matchCapabilities(intent: Intent, capabilities: Capability[]): MatchResult;

  // Score the quality of a capability match
  scoreMatch(intent: Intent, capabilities: Capability[]): number;
}
```

### 2. Capability Registry

Maintains a registry of all available capabilities across services.

```typescript
interface CapabilityRegistry {
  // Register a capability provider
  register(provider: CapabilityProvider): void;

  // Query capabilities matching criteria
  query(criteria: CapabilityQuery): Capability[];

  // Get capabilities for a specific provider
  getProviderCapabilities(providerId: string): Capability[];
}
```

### 3. Negotiation Engine

Handles the back-and-forth negotiation between parties.

```typescript
interface NegotiationEngine {
  // Start a negotiation session
  startNegotiation(intent: Intent): NegotiationSession;

  // Propose a contract
  propose(session: NegotiationSession, contract: Contract): ProposalResult;

  // Counter-propose
  counterPropose(
    session: NegotiationSession,
    modifications: ContractMod[],
  ): ProposalResult;

  // Accept or reject
  finalize(
    session: NegotiationSession,
    decision: "accept" | "reject",
  ): ContractResult;
}
```

### 4. Token Service

Issues and validates execution tokens.

```typescript
interface TokenService {
  // Issue a token for an agreed contract
  issueToken(contract: SignedContract): ExecutionToken;

  // Validate a token before execution
  validateToken(token: string): TokenValidation;

  // Revoke a token
  revokeToken(tokenId: string, reason: string): void;
}
```

### 5. Enforcement Engine

Monitors execution and enforces contract compliance.

```typescript
interface EnforcementEngine {
  // Start monitoring an execution
  startMonitoring(token: ExecutionToken): MonitoringSession;

  // Check if an action is allowed
  checkAction(session: MonitoringSession, action: Action): ActionDecision;

  // Record an action for audit
  recordAction(
    session: MonitoringSession,
    action: Action,
    result: ActionResult,
  ): void;

  // Handle violations
  handleViolation(session: MonitoringSession, violation: Violation): void;
}
```

## Implementation Steps

### Step 1: Define Your Intent Schema

Start by defining the intents your system will understand:

```yaml
intents:
  - id: code-review
    description: Review code for quality and security
    required_goals:
      - find-issues
    optional_goals:
      - suggest-fixes
      - check-security

  - id: deploy-service
    description: Deploy a service to an environment
    required_goals:
      - successful-deployment
    constraints:
      - environment-must-be-specified
```

### Step 2: Define Your Capability Vocabulary

Map your services to the capability vocabulary:

```yaml
services:
  - id: code-analyzer
    capabilities:
      - action: analyze
        scope: [repository]
        confidence: 0.95
      - action: suggest
        scope: [code]
        confidence: 0.85
    limitations:
      - action: write
        scope: [repository]
        reason: read-only service
```

### Step 3: Implement the Negotiation Flow

```typescript
async function negotiate(intent: Intent): Promise<Contract | null> {
  // 1. Find matching capabilities
  const capabilities = await registry.query({ matchesIntent: intent });

  // 2. Score and rank matches
  const ranked = capabilities
    .map((c) => ({ capability: c, score: engine.scoreMatch(intent, c) }))
    .sort((a, b) => b.score - a.score);

  // 3. Check constraints
  const valid = ranked.filter((r) =>
    satisfiesConstraints(r.capability, intent.constraints),
  );

  // 4. Build contract proposal
  if (valid.length === 0) return null;

  return buildContract(intent, valid[0].capability);
}
```

### Step 4: Implement Token-Based Execution

```typescript
async function executeWithToken(token: ExecutionToken, action: Action) {
  // Validate token
  const validation = tokenService.validateToken(token);
  if (!validation.valid) throw new TokenError(validation.reason);

  // Check action is allowed
  const decision = enforcement.checkAction(session, action);
  if (decision.denied) throw new ActionDenied(decision.reason);

  // Execute
  const result = await performAction(action);

  // Record for audit
  enforcement.recordAction(session, action, result);

  return result;
}
```

## Testing Strategy

### Unit Tests

- Intent parsing and validation
- Capability matching algorithms
- Constraint satisfaction

### Integration Tests

- Full negotiation flow
- Token issuance and validation
- Multi-party negotiations

### Property-Based Tests

- Negotiation always terminates
- Valid tokens always validate
- Violations always trigger rollback

### Security Tests

- Token forgery resistance
- Privilege escalation prevention
- Audit log integrity

## Deployment Considerations

1. **High Availability**: Negotiation and token services must be HA
2. **Latency**: Keep negotiation under 100ms for interactive use
3. **Audit Storage**: Plan for high-volume audit log storage
4. **Key Management**: Secure token signing keys
5. **Monitoring**: Alert on negotiation failures and violations
