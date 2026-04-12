# Debug Template

Template for `.planning/debug/[slug].md` — active debug session tracking.

---

## File Template

```markdown
---
status: gathering | investigating | fixing | verifying | awaiting_human_verify | resolved
trigger: "[verbatim user input]"
current_node_id: [ID of the active graph node]
created: [ISO timestamp]
updated: [ISO timestamp]
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: [current theory being tested]
test: [how testing it]
expecting: [what result means if true/false]
next_action: [immediate next step]

## Symptoms
<!-- Written during gathering, then immutable -->

expected: [what should happen]
actual: [what actually happens]
errors: [error messages if any]
reproduction: [how to trigger]
started: [when it broke / always broken]

## Eliminated
<!-- APPEND only - prevents re-investigating after context reset -->

- hypothesis: [theory that was wrong]
  evidence: [what disproved it]
  timestamp: [when eliminated]

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: [when found]
  checked: [what was examined]
  found: [what was observed]
  implication: [what this means]

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: [empty until found]
fix: [empty until applied]
verification: [empty until verified]
files_changed: []
```

---

<section_rules>

**Frontmatter (status, trigger, timestamps):**
- `status`: OVERWRITE - reflects current phase
- `trigger`: IMMUTABLE - verbatim user input, never changes
- `created`: IMMUTABLE - set once
- `updated`: OVERWRITE - update on every change

**Current Focus:**
- OVERWRITE entirely on each update
- Always reflects what the agent is doing RIGHT NOW
- If the agent reads this after context reset, it knows exactly where to resume
- Fields: hypothesis, test, expecting, next_action

**Symptoms:**
- Written during initial gathering phase
- IMMUTABLE after gathering complete
- Reference point for what we're trying to fix
- Fields: expected, actual, errors, reproduction, started

**Eliminated:**
- APPEND only - never remove entries
- Prevents re-investigating dead ends after context reset
- Each entry: hypothesis, evidence that disproved it, timestamp

**Evidence:**
- APPEND only - never remove entries
- Facts discovered during investigation
- Each entry: timestamp, what checked, what found, implication
- Builds the case for root cause

**Resolution:**
- OVERWRITE as understanding evolves
- Final state shows confirmed root cause and verified fix
- Fields: root_cause, fix, verification, files_changed

</section_rules>
