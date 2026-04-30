# Layered Progressive Disclosure Design

## Goal

Replace the current "load everything" context model in sp-* workflows with a
layered progressive disclosure system. Every command—from a single-line typo fix
to a full feature specification—pays approximately the same context-loading cost
today. The new model should make the cost proportional to task complexity: a
trivial task reads ~300 tokens of navigation + target summary, while a heavy
task unfolds through four information layers on demand.

## Problem Summary

Ten structural problems were identified across three rounds of review of the
project-map documentation and sp-* workflow commands:

| # | Problem | Impact |
|---|---------|--------|
| 1 | All commands load identical context regardless of complexity | Token waste on every invocation |
| 2 | Freshness check on trivial commands can trigger full rescan | Disproportionate cost |
| 3 | No layered information model — flat docs mix routing, summary, and detail | Reader can't stop at the right depth |
| 4 | Same knowledge appears in 3-5 docs without a declared authority | Maintenance drift, confusion |
| 5 | Command boundaries (trivial/light/heavy) judged subjectively | Wrong workflow chosen |
| 6 | Dispatch mode is subagent-mandatory for all commands including one-line fixes | Overhead exceeds work |
| 7 | Pre-analysis protocols duplicated across commands with different vocabulary | Cognitive load, non-interoperable outputs |
| 8 | Core modules have no docs but this is not explicitly marked | Silent gaps trigger unnecessary rescans |
| 9 | Workflow constraints (forbidden actions) are declaration-only with no gate check | Boundary violations undetected |
| 10 | Documents not bound to source version; staleness is binary and triggers full rebuild | All-or-nothing freshness |

## Design

### 1. The Onion Model: Four-Layer Information Architecture

Every piece of project knowledge lives in exactly one layer. Higher layers are
indexes into lower layers. A reader stops at the shallowest layer that answers
their question.

```
Layer 1 (路由层) — Task-to-document routing matrix, <50 lines
  "Which document should I open?"
  
Layer 2 (摘要层) — Module summary cards, <10 lines per module
  "What is this module? Is it worth reading deeper?"
  
Layer 3 (详情层) — Full module documentation, sectioned by topic
  "How does it work? How do I extend it? How do I test it?"
  
Layer 4 (源码层) — Source code
  "What does the code actually say?"
```

**Layer constraints:**

- Each layer's sole job is helping the reader decide whether to enter the next
  layer
- Layer 2 must not contain enumerations, protocol sequences, or configuration
  lists that belong in Layer 3
- Layer 3 sections must carry a "who needs this" prefix so readers can skip
- Any knowledge point has exactly one authoritative layer; all other layers
  reference it by link

### 2. Context Loading Gradient

Each sp-* command loads only the layers it needs. No command loads a deeper
layer before exhausting the shallower one.

| Command | Layer 1 | Layer 2 | Layer 3 | Layer 4 |
|---------|---------|---------|---------|---------|
| sp-fast | routing table | — | — | on-demand |
| sp-quick | routing table | target summary cards | 1-2 module docs (target sections only) | on-demand |
| sp-debug | routing table | target summary + workflow map | affected module docs | on-demand |
| sp-specify | routing table | all summary cards | affected module docs | on-demand |
| sp-plan | routing table | all summary cards | affected module docs + data models | on-demand |
| sp-tasks | routing table | per-plan decision | — | — |
| sp-implement | routing table | target summary | task-scoped module docs | on-demand |

**Loading order:** route first, then verify freshness of only the routed
target, then descend into details. Do not verify global freshness before knowing
what is relevant.

### 3. Freshness Layered Governance

Replace the current binary fresh/stale check with a layered, version-bound model:

- Every document records the source version (commit hash) at generation time
- Staleness is computed per-layer, not globally:
  - Layer 1 (routing): almost never stale (modules rarely appear/disappear)
  - Layer 2 (summary): changes slowly (entry interfaces are stable)
  - Layer 3 (detail): changes faster (protocols, config, internal structure)
- Staleness is a spectrum, not a flag: `current / possibly-stale / confirmed-stale`
- Trivial commands skip freshness checks entirely
- Light commands check only their target document's Layer 2 freshness; stale
  produces a warning but does not block
- Heavy commands enforce freshness on target Layer 3; stale triggers a scoped
  re-scan, not a global rebuild

### 4. Single Source of Truth

Each technical detail has exactly one authoritative document. Other documents
reference it with a one-line summary and a link.

**Rules:**
- Architecture summary cards (Layer 2) reference module docs (Layer 3) as
  authority for all detail
- Integration docs reference module docs for per-module technical content; they
  own only the cross-module interaction descriptions
- Workflow docs own end-to-end process descriptions; they reference architecture
  and module docs for per-step technical detail
- If a structured data file already encodes a relationship (e.g., dependency
  graph in relations.json), workflows must query it rather than re-deriving the
  same information from prose documents

**Document relationship declarations:** Every document states its relationship
to others explicitly: "This document is the summary of X; see Y for full
details" or "This document is the authoritative source for Z; all other
references to Z should point here."

### 5. Command Boundary & Handoff

Replace subjective "truly trivial" / "small but non-trivial" gates with
objective criteria:

| Gate | Criteria |
|------|----------|
| Trivial | ≤3 files, no shared registration surface, no protocol/contract boundary, no dependency changes |
| Light | ≤10 files, or touches one registration surface, or one dependency change |
| Heavy | >10 files, or crosses module boundary, or new API/contract, or architectural change |

**Escalation and de-escalation:**
- Light → Heavy: scope creep detected mid-execution
- Heavy → Light: root cause confirmed, scope narrows
- Debug → Light: error location + repro steps + impact surface all known
  (fast-path, skip observer framing)

**Fast-path for debug:** When the caller provides exact error location, clear
reproduction steps, and bounded impact surface, the observer framing stage is
skipped. The command proceeds directly to reproduction gate.

### 6. Shared Pre-Analysis Protocol

Extract the common "understand before acting" framework shared by sp-specify and
sp-debug into a single protocol. Each command defines only its specialized
phases; the shared output format is:

- Scope boundary
- Key constraints
- Affected surface area
- Known unknowns
- Recommended next step

Pre-analysis results from one command are recognized by other commands — if
analysis is already complete, do not restart it.

### 7. Dispatch Mode Gradient

Dispatch mode follows task complexity, not a one-size-fits-all rule:

| Command Tier | Dispatch Mode |
|-------------|---------------|
| Trivial (sp-fast) | leader-direct — no subagent dispatch |
| Light (sp-quick, sp-debug) | subagent-preferred, leader-inline fallback allowed |
| Heavy (sp-specify, sp-plan, sp-tasks, sp-implement) | subagent-mandatory |

**Fallback:** When subagent dispatch is unavailable, record the reason and fall
back to leader-inline. The fallback path is a designed mode, not an exception.

### 8. Gap Transparency

Every module in the knowledge map must carry an explicit documentation status:

- `documented` — Layer 3 doc exists
- `indexed-only` — Layer 2 summary card exists, no Layer 3 doc
- `gap` — no documentation; source code is the only reference

Scan-time discovered gaps must propagate to the map state file and architecture
document's "known unknowns" section. Planned vs. actual documentation output
differences must be tracked as unmet targets.

Reverse coverage validation covers both critical and important paths; important
paths that lack documentation are explicitly listed as gaps, not silently
omitted.

### 9. Constraint Enforcement Ladder

Workflow constraints (e.g., "sp-specify must not edit source code") currently
rely on declarations alone. The enforcement ladder is:

```
Level 1: Automated verification (ideal — e.g., tool-enforced layer boundaries)
Level 2: Gate self-check (explicit confirmation output at phase boundaries)
Level 3: Pure declaration (baseline — written constraint with no verification)
```

For workflow constraints where automated verification is impractical, gate
self-checks are required at key phase transitions. A gate self-check is an
explicit output confirming: "I have not performed any forbidden action since the
last gate."

### 10. Source Authority Declaration

Establish an explicit trust hierarchy when documents and source code conflict:

```
Source code > Layer 3 (detail docs) > Layer 2 (summary cards) > Layer 1 (routing table)
```

When a conflict is discovered, trust the higher-authority source, and flag the
lower-authority source with a stale marker for later correction.

Every document records:
- The commit hash it was generated from
- The specific source files it was derived from
- The confidence level and its basis (which files were actually read vs.
  inferred from other documents)

## Design Principles

1. **Onion Model** — Route → Summary → Detail → Source. Each layer's sole job
   is helping decide whether to enter the next.
2. **Single Source of Truth** — Every knowledge point is authoritative in
   exactly one layer. All others index by reference.
3. **Complexity-Graded Loading** — Trivial commands stop at Layer 1+target
   summary. Heavy commands unfold layer by layer.
4. **Layered Freshness** — Different layers have different staleness
   probabilities. Local staleness does not trigger global rebuild.
5. **Objective Command Gates** — File count, registration surface,
   protocol/contract boundary, and root-cause certainty determine command tier.
6. **Explicit Command Handoffs** — Escalation conditions, de-escalation
   conditions, and inter-command pre-analysis recognition are defined.
7. **Gap Transparency** — Undocumented modules, untracked gaps, and unmet scan
   targets are explicitly marked, never silently skipped.
8. **Gate Self-Check** — Where automated verification is infeasible, explicit
   confirmation output at phase boundaries replaces pure declaration.
9. **Version Binding** — Every document records its source commit. Staleness is
   computed from version distance, not from a binary flag.
10. **Structured Data Consumption** — Dependency graphs, interface indices, and
    other machine-readable data are consumed by workflows directly rather than
    re-derived from prose.

## Scope Note

This design addresses the information architecture and context-loading
strategies of the project-map and sp-* command system. It does not prescribe
specific file formats, template contents, or implementation details for
individual documents — those belong in the implementation plan.
