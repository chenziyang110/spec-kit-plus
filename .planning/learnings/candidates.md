# Candidate Learnings

Passive candidate learnings captured from `sp-xxx` workflows.

---

<!-- SPECKIT_LEARNING_DATA_BEGIN -->
[
  {
    "id": "LRN-20260427-153433-783083",
    "summary": "Boundary-sensitive sp-specify requests must explicitly close trigger, contract, lifecycle, failure, and configuration gaps before plan handoff.",
    "learning_type": "workflow_gap",
    "source_command": "sp-specify",
    "evidence": "Validated by template/test changes in templates/commands/specify.md, templates/spec-template.md, templates/alignment-template.md, templates/context-template.md, plus regression coverage in tests/test_specify_anti_surface_guidance.py and tests/test_alignment_templates.py.",
    "recurrence_key": "workflow_gap.boundary-sensitive-sp-specify-requests-must-explicitly-close-trigger-contract-lifecycle-failure-and-configuration-gaps-before-plan-handoff",
    "default_scope": "planning-heavy",
    "applies_to": [
      "sp-plan",
      "sp-quick",
      "sp-specify",
      "sp-tasks"
    ],
    "signal_strength": "medium",
    "status": "candidate",
    "first_seen": "2026-04-27T15:34:33Z",
    "last_seen": "2026-04-27T15:34:33Z",
    "occurrence_count": 1
  }
]
<!-- SPECKIT_LEARNING_DATA_END -->

## Managed Entries

### LRN-20260427-153433-783083 - Boundary-sensitive sp-specify requests must explicitly close trigger, contract, lifecycle, failure, and configuration gaps before plan handoff.

- Status: `candidate`
- Type: `workflow_gap`
- Source Command: `sp-specify`
- Recurrence Key: `workflow_gap.boundary-sensitive-sp-specify-requests-must-explicitly-close-trigger-contract-lifecycle-failure-and-configuration-gaps-before-plan-handoff`
- Scope: `planning-heavy`
- Applies To: sp-plan, sp-quick, sp-specify, sp-tasks
- Signal: `medium`
- Occurrence Count: 1
- First Seen: `2026-04-27T15:34:33Z`
- Last Seen: `2026-04-27T15:34:33Z`

#### Evidence

Validated by template/test changes in templates/commands/specify.md, templates/spec-template.md, templates/alignment-template.md, templates/context-template.md, plus regression coverage in tests/test_specify_anti_surface_guidance.py and tests/test_alignment_templates.py.

