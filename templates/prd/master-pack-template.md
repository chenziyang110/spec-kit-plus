# PRD Master Pack: [PROJECT]

**Run ID**: [RUN_ID]
**Project Mode**: [ui | service | mixed]
**Source Workspace**: [REPOSITORY_OR_SCOPE]
**Status**: Draft

This document is the single truth source for the PRD export suite. All exports must derive from this master pack. Do not maintain export-only facts that are absent from this file.

## Product Frame

- **Evidence/Inference/Unknown**: [Mark the confidence of the product summary.]
- **What exists now**: [Current-state product or service summary.]
- **Who it serves**: [Roles, users, operators, or systems.]
- **Core Value Proposition**: [Repository-backed statement of the product-defining value.]

## Audience and Roles

| Role | Description | Evidence/Inference/Unknown | Sources |
|------|-------------|----------------------------|---------|
| [ROLE] | [RESPONSIBILITY_OR_GOAL] | [Evidence] | [PATHS] |

## Capability Inventory

| Capability ID | Tier | Capability | User or System Value | Surfaces | Rules or Data | Depth Status | Evidence/Inference/Unknown | Export Destinations |
|---------------|------|------------|----------------------|----------|---------------|--------------|----------------------------|---------------------|
| [CAP-001] | [critical] | [CAPABILITY] | [VALUE] | [SCREENS_OR_ENTRYPOINTS] | [RULES_OR_ENTITIES] | [surface-covered | depth-qualified] | [Evidence] | [prd.md, ui-spec.md, service-spec.md] |

## Critical Capability Dossiers

### [CAP-001] [CAPABILITY]

#### Overview

- Purpose: [WHY_THIS_CAPABILITY_EXISTS]
- Tier: [critical | high]
- Evidence/Inference/Unknown: [CONFIDENCE]

#### Implementation Mechanisms

- [Mechanism name] -> [What it does and where it lives]

#### Format or Protocol Matrix

| Surface | Format / Protocol | Parser / Serializer | Constraints | Sources |
|---------|-------------------|---------------------|-------------|---------|
| [CONFIG_OR_API] | [FORMAT] | [PARSER] | [RULE] | [PATHS] |

#### Edge Cases and Failure Paths

- [Failure or compatibility case] -> [Handling behavior] -> [Sources]

#### Source Traceability

- [Claim] -> [file path or function path]

#### Unknowns and Inference Notes

- Unknown: [UNRESOLVED_GAP]
- Inference: [BOUNDED_INFERENCE]

## Surface Inventory

### UI Surfaces

- **[SCREEN_OR_ROUTE]**
  - Purpose: [PURPOSE]
  - Roles: [ROLES]
  - States: [LOADING_EMPTY_SUCCESS_ERROR_PERMISSION_STATES]
  - Evidence/Inference/Unknown: [CONFIDENCE]
  - Sources: [PATHS]

### Service Surfaces

- **[ENTRYPOINT_OR_JOB]**
  - Purpose: [PURPOSE]
  - Inputs and outputs: [CONTRACT_SUMMARY]
  - Failure behavior: [ERROR_OR_RETRY_RULES]
  - Evidence/Inference/Unknown: [CONFIDENCE]
  - Sources: [PATHS]

## Flows

| Flow | Trigger | Steps | Completion Signal | Evidence/Inference/Unknown | Sources |
|------|---------|-------|-------------------|----------------------------|---------|
| [FLOW] | [TRIGGER] | [STEPS] | [OUTCOME] | [Evidence] | [PATHS] |

## Data and Rule Model

### Entities

- **[ENTITY]**
  - Fields and relationships: [FIELDS_RELATIONSHIPS]
  - Lifecycle or state model: [STATES]
  - Evidence/Inference/Unknown: [CONFIDENCE]

### Rules

- **[RULE]**
  - Applies to: [CAPABILITY_OR_SURFACE]
  - Behavior: [RULE_BEHAVIOR]
  - Evidence/Inference/Unknown: [CONFIDENCE]

## Integrations and Dependencies

| Integration | Direction | Purpose | Constraints | Evidence/Inference/Unknown | Sources |
|-------------|-----------|---------|-------------|----------------------------|---------|
| [INTEGRATION] | [INBOUND_OR_OUTBOUND] | [PURPOSE] | [CONSTRAINTS] | [Evidence] | [PATHS] |

## Config Dossiers

| Config Surface | Path or Key | Default Value | Precedence | Runtime Effect | Evidence/Inference/Unknown | Sources |
|----------------|-------------|---------------|------------|----------------|----------------------------|---------|
| [CONFIG] | [PATH_OR_KEY] | [DEFAULT] | [PRECEDENCE] | [EFFECT] | [Evidence] | [PATHS] |

## Protocol Dossiers

| Boundary | Producer | Consumer | Protocol or Format | Field Mapping | Compatibility Notes | Evidence/Inference/Unknown | Sources |
|----------|----------|----------|--------------------|---------------|---------------------|----------------------------|---------|
| [BOUNDARY] | [PRODUCER] | [CONSUMER] | [PROTOCOL] | [MAPPING] | [NOTES] | [Evidence] | [PATHS] |

## State Machine Dossiers

| State Machine | State Set | Owner Surface | Transition Trigger | Guards or Preconditions | Failure and Recovery | Evidence/Inference/Unknown | Sources |
|---------------|-----------|---------------|--------------------|-------------------------|----------------------|----------------------------|---------|
| [MACHINE] | [STATES] | [SURFACE] | [TRIGGER] | [GUARDS] | [RECOVERY] | [Evidence] | [PATHS] |

## Error Semantic Dossiers

| Error or Condition | Trigger | Exposure | Recovery Behavior | User or System Impact | Evidence/Inference/Unknown | Sources |
|--------------------|---------|----------|-------------------|-----------------------|----------------------------|---------|
| [ERROR] | [TRIGGER] | [EXPOSURE] | [RECOVERY] | [IMPACT] | [Evidence] | [PATHS] |

## Verification Dossiers

| Surface or Capability | Minimum Verification Command | Locked Behavior | Existing Test and Fixture Signals | Parity Checkpoint | Evidence/Inference/Unknown | Sources |
|-----------------------|------------------------------|-----------------|-----------------------------------|-------------------|----------------------------|---------|
| [SURFACE] | [COMMAND] | [BEHAVIOR] | [TEST_OR_FIXTURE] | [CHECKPOINT] | [Evidence] | [PATHS] |

## Evidence, Inference, and Unknown Registry

### Evidence

- [Claim] -> [Source path or observed behavior]

### Inference

- [Inferred product meaning] -> [Evidence basis and confidence]

### Unknown

- [Unknown item] -> [Why evidence is insufficient]

## Reconstruction Risk Register

| Critical Gap | Affected Capability or Surface | Evidence Status | Fidelity Risk | Mitigation or Follow-Up | Sources |
|--------------|--------------------------------|-----------------|---------------|-------------------------|---------|
| [GAP] | [CAPABILITY_OR_SURFACE] | [Evidence/Inference/Unknown] | [RISK] | [FOLLOW_UP] | [PATHS] |

## Coverage and Export Map

| Master Item | Tier | Depth Status | prd.md | ui-spec.md | service-spec.md | flows-and-ia.md | data-rules-appendix.md | config-contracts.md | protocol-contracts.md | state-machines.md | error-semantics.md | verification-surface.md | reconstruction-risks.md | internal-implementation-brief.md |
|-------------|------|--------------|--------|------------|-----------------|-----------------|------------------------|---------------------|-----------------------|-------------------|--------------------|-------------------------|-------------------------|----------------------------------|
| [CAP-001] | [critical] | [depth-qualified] | [yes] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes] |

## Export Landing Map

| Export | Purpose | Required Master Sections | Evidence/Inference/Unknown Handling |
|--------|---------|--------------------------|-------------------------------------|
| `prd.md` | Reader-facing product requirements | Product Frame, Capability Inventory, Critical Capability Dossiers | Preserve confidence on consequential claims. |
| `ui-spec.md` | UI reconstruction surface | UI Surfaces, Flows, State Machine Dossiers, Error Semantic Dossiers | Keep UI-only gaps visible as Unknown. |
| `service-spec.md` | Service and entrypoint reconstruction surface | Service Surfaces, Protocol Dossiers, Error Semantic Dossiers | Preserve boundary and compatibility evidence. |
| `flows-and-ia.md` | Navigation and task movement | Flows, Surface Inventory, State Machine Dossiers | Mark inferred transitions explicitly. |
| `data-rules-appendix.md` | Data, rules, and terminology | Data and Rule Model, Config Dossiers, State Machine Dossiers | Separate field evidence from inferred semantics. |
| `config-contracts.md` | Configuration defaults, precedence, and effects | Config Dossiers | Unknown defaults stay unresolved. |
| `protocol-contracts.md` | Boundary contracts and mappings | Protocol Dossiers | Compatibility claims require sources. |
| `state-machines.md` | State sets, transitions, guards, and recovery | State Machine Dossiers | Do not collapse unresolved states into inferred states. |
| `error-semantics.md` | Error triggers, exposure, and recovery | Error Semantic Dossiers | Preserve user-visible versus internal behavior. |
| `verification-surface.md` | Minimum verification and parity checks | Verification Dossiers | Distinguish runnable evidence from inferred checks. |
| `reconstruction-risks.md` | Critical gaps and fidelity risks | Evidence, Inference, and Unknown Registry | Keep blocking Unknowns prominent. |
| `internal-implementation-brief.md` | Code mapping and planning handoff | Source Traceability, Verification Dossiers | Do not introduce export-only facts. |

## Export Completeness Check

- [ ] every master capability appears in at least one export.
- [ ] Every relevant screen or service surface has a documented home.
- [ ] Rules and entities are not stranded only in evidence notes.
- [ ] Config, protocol, state, error, verification, and reconstruction-risk dossiers have export homes.
- [ ] Unknowns remain visible where required.
- [ ] No unresolved placeholders or contradictory claims remain.
