# Project Learnings

Confirmed project learnings that are reusable across later `sp-xxx` workflows
but are not yet strong enough to become project rules or constitution-level
principles.

Promote items here after recurrence, explicit confirmation, or clear
cross-stage usefulness. Keep noisy or unproven observations in passive candidate
learning files until they mature.

---

## Tracked atlas refresh baseline

- type: workflow_state
- signal: high
- recurrence_key: project-map-tracked-atlas-baseline
- applies_to: map-build, verification, git-workflow
- summary: `.specify/project-map/**` is stable project knowledge and should be committed with the handbook; after that commit, rerun `project-map complete-refresh` and commit the status files so `last_mapped_commit` points at the atlas-containing commit.
- evidence: `.gitignore` unignores `.specify/project-map/**` and `.specify/memory/project-*.md` while keeping `.specify/runtime/**` and `.specify/teams/**` ignored; `project-map check --format json` reports the new untracked atlas files as high-impact changes until committed.
