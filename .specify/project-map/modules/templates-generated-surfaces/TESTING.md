# Templates And Generated Surfaces Testing

**Last Updated:** 2026-04-30
**Coverage Scope:** generated workflow templates, passive skills, scripts, packaging assets, and integration outputs.
**Primary Evidence:** `worker-results/testing-verification.json`, `integrations-generated-surfaces.json`, `packaging-release-config.json`
**Update When:** templates, scripts, passive skills, generated destinations, or packaging asset lists change.

## Smallest Trustworthy Checks

| Changed Surface | Check |
| --- | --- |
| Map scan/build templates | `pytest tests/test_map_scan_build_template_guidance.py -q` |
| Project-map templates | `pytest tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py -q` |
| Passive skills | `pytest tests/test_passive_skill_guidance.py tests/test_quick_skill_mirror.py -q` |
| Integration output paths/transforms | `pytest tests/integrations -q` |
| Freshness scripts | `pytest tests/test_project_map_freshness_scripts.py -q` |
| Packaged assets | `pytest tests/test_packaging_assets.py -q` |

## Regression-Sensitive Areas

- `sp-*` workflow names and generated skill namespaces.
- Argument placeholder transforms: `$ARGUMENTS`, `{{args}}`, `{{parameters}}`.
- Codex/Claude/Kimi/Antigravity skills-directory behavior.
- Copilot companion prompt and VS Code settings generation.
- Forge frontmatter transformations.
- Atlas and testing artifact sections asserted by template tests.

## Shared Test Dependencies

- Integration tests depend on both template text and adapter code.
- Packaging tests depend on `pyproject.toml` force-includes.
- Freshness script tests depend on Bash/PowerShell parity.
- Docs guidance tests may fail when workflow terminology changes.

## Minimum Verification

- Focused generated-surface check: `pytest tests/test_map_scan_build_template_guidance.py tests/test_passive_skill_guidance.py tests/integrations -q`
- Broader generated/package check: `pytest tests/test_packaging_assets.py tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py -q`
