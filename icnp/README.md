# Intent-and-Capability Negotiation Protocol (ICNP)

> **"Tell me what you want to achieve, what you are allowed to do, and under what constraints — and we will automatically agree (or refuse) on how to proceed."**

## Overview

ICNP is a **first-class, machine-readable protocol** for expressing intent, negotiating capabilities, and enforcing contracts between software components, services, agents, and humans-in-the-loop — **before** any data exchange or API call happens.

## The Problem ICNP Solves

Modern systems involve:

- Autonomous agents with varying trust levels
- Dynamically composed workflows
- Third-party tools with unknown capabilities
- Human approval gates
- Regulatory, cost, and safety constraints

Today, agreement between parties is:

- Hard-coded in configuration
- Implied through API contracts
- Enforced after failure (reactive)

**ICNP moves agreement before execution (proactive).**

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    ICNP Protocol Stack                          │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: Execution Binding                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Intent Token│──│ Audit Trail  │──│ Rollback Semantics    │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: Contract Negotiation                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Agreed Acts │──│ Forbidden    │──│ Constraints Solver    │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: Capability Disclosure                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Capabilities│──│ Limitations  │──│ Confidence Scores     │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Intent Declaration                                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Goals       │──│ Non-Goals    │──│ Constraints           │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Mesh Trust Model

ICNP builds on mesh trust principles where trust is:

- Distributed across participants
- Dynamically negotiated
- Verifiable at each step

### Intent-Based Networking

Inspired by IBN's Intent → Translation → Activation → Assurance cycle:

- **Intent**: What the requester wants to achieve
- **Translation**: Mapping intent to capabilities
- **Activation**: Executing agreed actions
- **Assurance**: Continuous verification

### Federated Execution

Like federated learning, ICNP supports:

- Distributed decision-making
- Local policy enforcement
- Global constraint satisfaction

## Use Cases

### Primary Use Cases

1. **Multi-Agent Workflow Communication** - Agents negotiate capabilities before exchanging data
2. **CI/CD Pipeline Orchestration** - Pipeline stages declare and negotiate permissions
3. **Cross-Organization API Integration** - B2B service negotiations with trust boundaries
4. **AI Agent Tool Access** - Safety constraints for autonomous agent actions
5. **Regulated Healthcare Workflows** - HIPAA/GDPR compliance enforcement

### Additional Use Cases

6. **Edge Computing** - Resource-constrained negotiation at the edge
7. **Financial Trading Compliance** - Pre-trade regulatory validation
8. **Multi-Cloud Orchestration** - Cost and data residency optimization
9. **Autonomous Vehicle Coordination** - Real-time V2V negotiation
10. **Smart Contract Pre-Negotiation** - Off-chain negotiation before on-chain execution

For detailed examples of each use case, see [Use Cases Documentation](./use-cases.md).

## Related Documents

- [Protocol Specification](./specification.md)
- [Intent Schema](./intent-schema.md)
- [Capability Vocabulary](./capability-vocabulary.md)
- [Implementation Guide](./implementation-guide.md)
- [Use Cases](./use-cases.md)

## Quick Start

See the [ICNP Workflow Template](../../../src/templates/builtin/icnp-protocol-design.yaml) for a complete design-to-deployment workflow.
