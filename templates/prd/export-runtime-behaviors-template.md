# Runtime Behaviors: [PROJECT]

**Run ID**: [RUN_ID]
**Derived From**: `master/master-pack.md`

This export describes observed startup, steady-state, background, shutdown, recovery, and operational behavior. It preserves Evidence/Inference/Unknown labels for every consequential claim.

## Runtime Entrypoints

| Entrypoint | Startup Inputs | Ready Signal | Long-Running Work | Shutdown | Evidence/Inference/Unknown |
|------------|----------------|--------------|-------------------|----------|----------------------------|
| [ENTRYPOINT] | [INPUTS] | [READY_SIGNAL] | [WORK] | [SHUTDOWN] | [Evidence] |

## Lifecycle And State

### [RUNTIME_SURFACE]

- Startup sequence: [SEQUENCE]
- Steady-state behavior: [BEHAVIOR]
- State and persistence: [STATE]
- Recovery / retry: [RECOVERY]
- Sources: [PATHS]
- Evidence/Inference/Unknown: [CONFIDENCE]

## Operational Failure Modes

| Failure | Detection | User / Operator Effect | Recovery | Sources |
|---------|-----------|------------------------|----------|---------|
| [FAILURE] | [DETECTION] | [EFFECT] | [RECOVERY] | [PATHS] |

## Unknowns And Verification Gaps

- [Unknown runtime behavior, impact, and smallest verification path.]
