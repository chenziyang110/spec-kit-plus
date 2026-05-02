# Service Specification: [PROJECT]

**Run ID**: [RUN_ID]
**Derived From**: `master/master-pack.md`
**Applies To Modes**: `service`, `mixed`

This export documents current service, API, CLI, worker, automation, or platform behavior. It must preserve Evidence/Inference/Unknown labels and avoid adding service facts that are absent from the master pack.

## Service Scope

- **Included service surfaces**: [API_CLI_JOBS_EVENTS]
- **Excluded or unknown service surfaces**: [EXCLUSIONS_OR_UNKNOWNS]
- **Evidence/Inference/Unknown**: [CONFIDENCE_SUMMARY]

## Capability Inventory

| Capability | Entrypoints | Entities Changed | Constraints | Evidence/Inference/Unknown |
|------------|-------------|------------------|-------------|----------------------------|
| [CAPABILITY] | [ENTRYPOINTS] | [ENTITIES] | [CONSTRAINTS] | [Evidence] |

## Entrypoint Inventory

| Entrypoint | Type | Inputs | Outputs | Auth or Trust Boundary | Evidence/Inference/Unknown |
|------------|------|--------|---------|------------------------|----------------------------|
| [ENTRYPOINT] | [API_CLI_JOB_EVENT] | [INPUTS] | [OUTPUTS] | [BOUNDARY] | [Evidence] |

## Capability Details

### [CAPABILITY]

- Purpose: [PURPOSE]
- Trigger: [TRIGGER]
- Processing summary: [PROCESSING]
- Data effects: [DATA_EFFECTS]
- Evidence/Inference/Unknown: [CONFIDENCE]

## Runtime and Dependency Constraints

- [Configuration, external dependency, platform constraint, rate limit, or operational assumption.]

## Service Flows

- **[FLOW]**
  - Trigger: [TRIGGER]
  - Invocation chain: [CHAIN]
  - Outcome: [OUTCOME]
  - Evidence/Inference/Unknown: [CONFIDENCE]

## Failure Paths

- [Validation failure, retry behavior, idempotency rule, degraded mode, or error response.]

## Service Unknowns

- [Unknown service behavior or missing repository evidence.]
