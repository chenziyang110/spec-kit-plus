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
- **Primary value**: [Repository-backed value statement.]

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

## Evidence, Inference, and Unknown Registry

### Evidence

- [Claim] -> [Source path or observed behavior]

### Inference

- [Inferred product meaning] -> [Evidence basis and confidence]

### Unknown

- [Unknown item] -> [Why evidence is insufficient]

## Coverage and Export Map

| Master Item | Tier | Depth Status | prd.md | ui-spec.md | service-spec.md | flows-and-ia.md | data-rules-appendix.md | internal-implementation-brief.md |
|-------------|------|--------------|--------|------------|-----------------|-----------------|------------------------|----------------------------------|
| [CAP-001] | [critical] | [depth-qualified] | [yes] | [yes/no] | [yes/no] | [yes/no] | [yes/no] | [yes] |

## Export Completeness Check

- [ ] every master capability appears in at least one export.
- [ ] Every relevant screen or service surface has a documented home.
- [ ] Rules and entities are not stranded only in evidence notes.
- [ ] Unknowns remain visible where required.
- [ ] No unresolved placeholders or contradictory claims remain.
