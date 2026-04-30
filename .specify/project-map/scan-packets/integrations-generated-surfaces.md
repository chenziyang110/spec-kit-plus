# MapScanPacket: integrations-generated-surfaces

- lane_id: integrations-generated-surfaces
- mode: read_only
- scope: integration registry, integration base classes, adapter-specific transforms, command templates, passive skills, generated-surface helper scripts.
- ledger_row_ids: L004, L005, L006

## required_reads

- `src/specify_cli/integrations/__init__.py`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/*/__init__.py`
- `src/specify_cli/integrations/*/scripts/update-context.*`
- `src/specify_cli/integrations/manifest.py`
- `templates/commands/*.md`
- `templates/command-partials/**/*.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `templates/project-map/**`
- `templates/testing/**`
- `templates/worker-prompts/*.md`
- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`

## excluded_paths

- `templates/passive-skills/*/theme-showcase.pdf`
- generated caches

## required_questions

- How do integration classes map shared templates into agent-specific file trees?
- Which integrations use Markdown, TOML, skills, prompts, workflows, rules, or custom transforms?
- Which template changes propagate to every generated project?
- Which scripts mirror or preserve context blocks for generated integrations?

## expected_outputs

- Supported integration map with special cases.
- Generated-surface propagation rules and risky adapter differences.
- Template ownership and verification routes.

## atlas_targets

- `.specify/project-map/root/CONVENTIONS.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- `.specify/project-map/modules/templates-generated-surfaces/OVERVIEW.md`
- `.specify/project-map/modules/templates-generated-surfaces/STRUCTURE.md`
- `.specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md`

## forbidden_actions

- Do not rewrite templates during evidence collection.
- Do not collapse integration-specific exceptions into generic markdown behavior.

## result_handoff_path

`.specify/project-map/worker-results/integrations-generated-surfaces.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/integrations tests/test_map_scan_build_template_guidance.py tests/test_passive_skill_guidance.py -q`

## blocked_conditions

- Integration registry or template directories are unreadable.
- Generated-surface path conventions cannot be determined.
