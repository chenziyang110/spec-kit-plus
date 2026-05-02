# Product Requirements Document: [PROJECT]

**Run ID**: [RUN_ID]
**Derived From**: `master/master-pack.md`
**Status**: Draft

This export is the primary reader-facing PRD. It must be derived from `master-pack.md` and preserve Evidence/Inference/Unknown labels for consequential claims.

## Document Summary

- **Product**: [PROJECT]
- **Current-state purpose**: [SUMMARY]
- **Project mode**: [ui | service | mixed]
- **Confidence summary**: [EVIDENCE_INFERENCE_UNKNOWN_BALANCE]

## Product Overview

[Explain what the project is, what it does today, and what value it provides.]

## Users and Roles

| Role | Need or Goal | Supported Capabilities | Evidence/Inference/Unknown |
|------|--------------|------------------------|----------------------------|
| [ROLE] | [NEED] | [CAPABILITIES] | [Evidence] |

## Scope and Boundaries

### In Scope

- [Current-state capability or product area]

### Out of Scope

- [Unsupported, deferred, or unknown area]

## Capability Overview

| Capability | Description | Primary User or System | Evidence/Inference/Unknown |
|------------|-------------|------------------------|----------------------------|
| [CAPABILITY] | [DESCRIPTION] | [ROLE_OR_SYSTEM] | [Evidence] |

## Critical Capability Notes

| Capability | Tier | Depth Status | Why It Matters | Evidence/Inference/Unknown |
|------------|------|--------------|----------------|----------------------------|
| [CAPABILITY] | [critical] | [depth-qualified | surface-covered | depth-gap] | [WHY_THIS_CAPABILITY_IS_CORE] | [Evidence] |

## Confidence and Unknown Handling

- `depth-qualified` means the master pack reconstructs the capability with mechanism-level detail and traceable evidence.
- `surface-covered` means the capability appears in repository surfaces but still lacks enough reconstruction depth to be treated as complete.

## Key Flows

- **[FLOW]**
  - Trigger: [TRIGGER]
  - Main path: [PATH]
  - Outcome: [OUTCOME]
  - Confidence: [Evidence/Inference/Unknown]

## Rule Summary

- [Business, validation, permission, or operational rule.]

## Dependency Summary

- [External service, library, runtime, configuration, or operational dependency.]

## Unknowns and Evidence Confidence

### Evidence-Backed Claims

- [Claim with source reference.]

### Inferences

- [Inference and evidence basis.]

### Unknowns

- [Unknown that remains unresolved.]

## Appendix Navigation

- UI specification: `ui-spec.md`
- Service specification: `service-spec.md`
- Flows and information architecture: `flows-and-ia.md`
- Data and rules appendix: `data-rules-appendix.md`
- Internal implementation brief: `internal-implementation-brief.md`
