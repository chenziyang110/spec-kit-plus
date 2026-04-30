# Deep Research: Webhook retry backoff

**Feature Branch**: `[003-webhook-retry-backoff]`
**Created**: 2026-04-29
**Status**: Ready for plan with constraints

## Feasibility Decision

- **Recommendation**: Proceed to `/sp.plan`
- **Reason**: The retry timing model was uncertain, but a disposable spike proved the scheduler can express the required backoff shape within acceptable drift.
- **Planning handoff readiness**: Complete with constraints

## Capability Feasibility Matrix

| Capability ID | Capability | Unknown Link | Evidence Needed | Proof Method | Result |
| --- | --- | --- | --- | --- | --- |
| CAP-001 | Schedule webhook retry backoff | Whether existing scheduler supports capped exponential retry timing | Runnable proof with representative delays | SPK-001, EVD-001 | constrained |

## Research Orchestration

- **Execution model**: subagents-first
- **Dispatch shape**: one-subagent
- **Execution surface**: native-subagents
- **Reason**: safe-one-subagent
- **Selected tracks**:
  - TRK-001 -> disposable spike write scope `research-spikes/webhook-retry-backoff/`
- **Join points**:
  - before final conflict resolution
  - before writing `Synthesis Decisions`
  - before writing `Planning Handoff`

## Research Agent Findings

| Track ID | Agent / Mode | Question | Evidence IDs | Confidence | Exit State | Planning Implication |
| --- | --- | --- | --- | --- | --- | --- |
| TRK-001 | one-subagent spike | Can the scheduler express capped exponential retry timing with acceptable drift? | SPK-001, EVD-001 | medium | constrained-but-plannable | Use PH-001 and PH-002 to preserve scheduler constraints |

## Evidence Quality Rubric

| Evidence ID | Supports | Source Tier | Source / Path | Reproduced Locally | Recency / Version | Confidence | Plan Impact | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPK-001 | CAP-001 / PH-001 / PH-002 | runnable-spike | `research-spikes/webhook-retry-backoff/` | yes | 2026-04-29 | medium | constraining | Uses synthetic delays, not production queue load |
| EVD-001 | CAP-001 / PH-001 | repo-evidence | `src/scheduler/retry_policy.py` | not applicable | not time-sensitive | high | constraining | Shows current scheduler primitives, not final feature behavior |

## Implementation Chain Evidence

### Webhook retry backoff

- **Capability ID**: CAP-001
- **Chain**: failed webhook delivery -> retry policy -> scheduler delay -> delivery worker retry attempt
- **Repository evidence**: EVD-001 shows existing retry policy primitives.
- **External evidence**: None needed.
- **Demo evidence**: SPK-001 proves capped exponential delays can be represented with current primitives.
- **Planning constraints**: PH-001 -> Reuse scheduler delay primitives; PH-002 -> include drift tolerance in validation.
- **Residual risk**: Production queue load may increase drift beyond the spike environment.

## Demo / Spike Evidence

- **Spike ID**: SPK-001
- **Spike**: webhook-retry-backoff
- **Hypothesis**: Existing scheduler delay primitives can express capped exponential retry timing.
- **Path**: `research-spikes/webhook-retry-backoff/`
- **Setup / env**: Local runtime with synthetic retry events.
- **Command**: `python research-spikes/webhook-retry-backoff/run.py`
- **Expected result**: Generated retry delays match 1m, 5m, 25m, and capped 60m windows within tolerance.
- **Actual result**: passed; observed synthetic drift stayed under the planning tolerance.
- **Evidence summary**: SPK-001 proves the timing model is plannable with explicit drift constraints.
- **Cleanup note**: Spike remains disposable under `research-spikes/`.
- **What this does not prove**: Does not prove production queue behavior under high load.
- **Planning implication**: `/sp.plan` should reuse scheduler primitives and design drift-aware tests.

## Spike Log

- **Spike**: webhook-retry-backoff
- **Hypothesis**: Existing scheduler delay primitives can express capped exponential retry timing.
- **Path**: `research-spikes/webhook-retry-backoff/`
- **Command**: `python research-spikes/webhook-retry-backoff/run.py`
- **Result**: passed
- **Evidence summary**: Retry windows matched expected capped backoff within tolerance.

## Synthesis Decisions

- **Recommended approach**: PH-001 -> Reuse existing scheduler delay primitives and add a retry-policy layer for capped exponential backoff.
- **Rejected options**:
  - Add a separate timer service -> rejected because SPK-001 proves existing primitives are sufficient for planning.
- **Conflict resolution**:
  - No source conflict found.
- **Plan constraints**:
  - PH-002 -> Treat drift tolerance as a validation requirement, not an implementation detail.

## Planning Handoff

- **Handoff IDs**: PH-001, PH-002
- **Recommended approach**: PH-001 -> Reuse existing scheduler delay primitives for capped exponential retry; trace to CAP-001 / TRK-001 / SPK-001 / EVD-001.
- **Architecture implications**: PH-001 -> Add retry policy composition around the existing scheduler instead of introducing a separate timer service.
- **Module boundaries**: PH-001 -> Retry policy owns delay calculation; scheduler owns execution timing.
- **API / library choices**: PH-001 -> Use existing scheduler API and retry policy helpers.
- **Data flow notes**: PH-001 -> Failed delivery emits retry event, retry policy calculates next delay, scheduler enqueues next attempt.
- **Demo artifacts to reference**: PH-001 -> `research-spikes/webhook-retry-backoff/`, SPK-001.
- **Constraints `/sp.plan` must preserve**:
  - PH-001 -> Do not introduce a second scheduling mechanism.
  - PH-002 -> Include explicit drift tolerance in the design and validation plan.
- **Validation implications**: PH-002 -> Plan unit tests for delay calculation and an integration-style scheduler drift check.
- **Residual risks requiring design mitigation**:
  - PH-002 -> Production queue load may increase drift beyond the spike result.
- **Decisions already proven by research**:
  - PH-001 -> Existing scheduler primitives can support the required backoff shape.

## Planning Traceability Index

| Handoff ID | Plan Consumer | Supported By | Evidence Quality | Required Plan Action |
| --- | --- | --- | --- | --- |
| PH-001 | architecture / module boundary | CAP-001, TRK-001, SPK-001, EVD-001 | medium / constraining | Reuse scheduler primitives and add retry-policy composition |
| PH-002 | validation / risk | CAP-001, TRK-001, SPK-001 | medium / constraining | Plan drift-aware validation and mitigation |

## Sources

- `src/scheduler/retry_policy.py` -> shows current scheduler primitives.
- `research-spikes/webhook-retry-backoff/` -> runnable proof for capped retry timing.

## Next Command

- `/sp.plan`
