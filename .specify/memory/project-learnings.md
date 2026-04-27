# Project Learnings

Confirmed project learnings that are reusable across later `sp-xxx` workflows
but are not yet strong enough to become project rules or constitution-level
principles.

Promote items here after recurrence, explicit confirmation, or clear
cross-stage usefulness. Keep noisy or unproven observations in passive candidate
learning files until they mature.

---

<!-- SPECKIT_LEARNING_DATA_BEGIN -->
[
  {
    "id": "LRN-20260427-132535-834750",
    "summary": "Learning hooks must turn self-learning from prompt guidance into cross-workflow enforcement",
    "learning_type": "project_constraint",
    "source_command": "sp-plan",
    "evidence": "User explicitly confirmed the hook design should not be forgotten: add workflow.learning.signal/review/capture/inject events; use signal as soft prompt, review as hard closeout gate, capture as semi-automatic candidate recording, and inject to route each learning back into the right workflow/docs/rules surface. This applies across sp-* workflows, not just sp-debug.",
    "recurrence_key": "learning.hooks.cross-workflow-enforcement",
    "default_scope": "global",
    "applies_to": [
      "sp-debug",
      "sp-fast",
      "sp-implement",
      "sp-plan",
      "sp-quick",
      "sp-specify",
      "sp-tasks"
    ],
    "signal_strength": "high",
    "status": "confirmed",
    "first_seen": "2026-04-27T13:25:35Z",
    "last_seen": "2026-04-27T13:25:35Z",
    "occurrence_count": 1
  }
]
<!-- SPECKIT_LEARNING_DATA_END -->

## Managed Entries

### LRN-20260427-132535-834750 - Learning hooks must turn self-learning from prompt guidance into cross-workflow enforcement

- Status: `confirmed`
- Type: `project_constraint`
- Source Command: `sp-plan`
- Recurrence Key: `learning.hooks.cross-workflow-enforcement`
- Scope: `global`
- Applies To: sp-debug, sp-fast, sp-implement, sp-plan, sp-quick, sp-specify, sp-tasks
- Signal: `high`
- Occurrence Count: 1
- First Seen: `2026-04-27T13:25:35Z`
- Last Seen: `2026-04-27T13:25:35Z`

#### Evidence

User explicitly confirmed the hook design should not be forgotten: add workflow.learning.signal/review/capture/inject events; use signal as soft prompt, review as hard closeout gate, capture as semi-automatic candidate recording, and inject to route each learning back into the right workflow/docs/rules surface. This applies across sp-* workflows, not just sp-debug.
