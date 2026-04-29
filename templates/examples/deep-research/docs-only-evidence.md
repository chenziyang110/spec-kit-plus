# Deep Research: OAuth callback validation

**Feature Branch**: `[002-oauth-callback-validation]`
**Created**: 2026-04-29
**Status**: Ready for plan

## Feasibility Decision

- **Recommendation**: Proceed to `/sp.plan`
- **Reason**: Current repository adapter boundaries and primary provider documentation prove the callback verification chain without a disposable spike.
- **Planning handoff readiness**: Complete

## Capability Feasibility Matrix

| Capability ID | Capability | Unknown Link | Evidence Needed | Proof Method | Result |
| --- | --- | --- | --- | --- | --- |
| CAP-001 | Validate OAuth callback signatures | Provider signature shape and local adapter fit | Primary docs plus repository adapter pattern | EVD-001, EVD-002 | proven |

## Research Orchestration

- **Strategy**: single-lane
- **Reason**: no-safe-batch
- **Selected tracks**:
  - TRK-001 -> docs and repository evidence packet
- **Join points**:
  - before final conflict resolution
  - before writing `Synthesis Decisions`
  - before writing `Planning Handoff`

## Research Agent Findings

| Track ID | Agent / Mode | Question | Evidence IDs | Confidence | Exit State | Planning Implication |
| --- | --- | --- | --- | --- | --- | --- |
| TRK-001 | single-lane research | Can callback signatures be validated inside the existing adapter boundary? | EVD-001, EVD-002 | high | enough-to-plan | Use PH-001 to keep validation inside the provider adapter |

## Evidence Quality Rubric

| Evidence ID | Supports | Source Tier | Source / Path | Reproduced Locally | Recency / Version | Confidence | Plan Impact | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVD-001 | CAP-001 / PH-001 | primary-docs | `references.md#oauth-provider-callback-signatures` | not applicable | 2026-04-29 | high | constraining | Does not prove provider uptime or malformed network retries |
| EVD-002 | CAP-001 / PH-001 | repo-evidence | `src/integrations/provider_adapter.py` | not applicable | not time-sensitive | high | constraining | Shows boundary shape, not the final feature code |

## Implementation Chain Evidence

### OAuth callback validation

- **Capability ID**: CAP-001
- **Chain**: callback request -> provider adapter -> signature verifier -> normalized auth result
- **Repository evidence**: EVD-002 shows the existing adapter owns provider-specific request normalization.
- **External evidence**: EVD-001 documents the required signature header and payload canonicalization.
- **Demo evidence**: Not needed; documentation and repository evidence are enough for planning.
- **Planning constraints**: PH-001 -> Keep provider-specific validation inside the adapter.
- **Residual risk**: Provider behavior may differ in staging; plan should include fixture-based verification.

## Demo / Spike Evidence

- **Spike ID**: Not needed
- **Spike**: Not needed
- **Planning implication**: No `research-spikes/` artifact is required.

## Synthesis Decisions

- **Recommended approach**: PH-001 -> Add signature validation inside the provider adapter, using the documented header and canonical payload format from EVD-001 and the repository boundary from EVD-002.
- **Rejected options**:
  - Validate in the controller -> rejected because it leaks provider-specific behavior across the adapter boundary.
- **Conflict resolution**:
  - No source conflict found.
- **Plan constraints**:
  - PH-001 -> Preserve the provider adapter as the integration boundary.

## Planning Handoff

- **Handoff IDs**: PH-001
- **Recommended approach**: PH-001 -> Implement callback signature validation inside the provider adapter; trace to CAP-001 / TRK-001 / EVD-001 / EVD-002.
- **Architecture implications**: PH-001 -> Preserve the controller-to-adapter boundary and keep provider-specific canonicalization out of application services.
- **Module boundaries**: PH-001 -> Adapter owns provider headers, canonical payload construction, and verifier errors.
- **API / library choices**: PH-001 -> Use the existing crypto helper unless `/sp.plan` finds a project-standard verifier abstraction.
- **Data flow notes**: PH-001 -> Raw callback request enters adapter, adapter returns a normalized validation result.
- **Demo artifacts to reference**: PH-001 -> Not needed; cite EVD-001 and EVD-002.
- **Constraints `/sp.plan` must preserve**:
  - PH-001 -> Do not move provider-specific validation into shared controller code.
- **Validation implications**: PH-001 -> Plan fixture-based tests for valid signature, invalid signature, missing header, and timestamp drift.
- **Residual risks requiring design mitigation**:
  - PH-001 -> Staging provider payloads may expose undocumented edge cases.
- **Decisions already proven by research**:
  - PH-001 -> The implementation chain is plannable without a disposable spike.

## Planning Traceability Index

| Handoff ID | Plan Consumer | Supported By | Evidence Quality | Required Plan Action |
| --- | --- | --- | --- | --- |
| PH-001 | module boundary / validation | CAP-001, TRK-001, EVD-001, EVD-002 | high / constraining | Preserve adapter ownership and plan signature fixtures |

## Sources

- `references.md#oauth-provider-callback-signatures` -> documents signature headers and payload canonicalization.
- `src/integrations/provider_adapter.py` -> shows the existing adapter boundary.

## Next Command

- `/sp.plan`
