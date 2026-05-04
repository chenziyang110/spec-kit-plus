# Downstream Testing Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Spec Kit Plus so generated downstream projects treat `.specify/testing/*` as a strict testing control plane with strong `small + medium + fast smoke` defaults, newcomer-focused playbooks, and binding reuse across `sp-test-scan`, `sp-test-build`, and later `sp-*` workflows.

**Architecture:** Strengthen the product in four layers. First, tighten the downstream testing artifact templates so each file has one strict responsibility and carries the new control-plane semantics. Second, update the shared workflow templates so `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-debug`, `sp-quick`, and `sp-fast` consume the testing artifacts consistently. Third, extend runtime inventory and packet context so Python and TypeScript or JavaScript projects receive stronger defaults and later execution packets automatically read the testing contract surfaces. Fourth, lock the behavior with regression tests spanning template guidance, inventory heuristics, and generated integration output.

**Tech Stack:** Python 3, Typer CLI, Markdown workflow templates, JSON testing artifacts, pytest

---

## File Structure

### Primary product surfaces

- `templates/testing/test-scan-template.md`
  - Human-readable scan artifact template. Must gain strict module evidence, scenario matrix, and command-tier language.
- `templates/testing/test-build-plan-template.md`
  - Human-readable build-wave template. Must show `fast smoke`, `focused`, `full`, layer expectations, and lane packet fields clearly.
- `templates/testing/test-build-plan-template.json`
  - Machine-readable lane contract. Must become more explicit about command tiers and scenario-driven lane intent without turning into prose.
- `templates/testing/testing-contract-template.md`
  - Downstream binding policy surface. Must define covered modules, mandatory triggers, and command-tier expectations.
- `templates/testing/testing-playbook-template.md`
  - Downstream operator guide. Must expose newcomer-friendly module rules and concrete `fast smoke`, `focused`, `full` command slots.
- `templates/testing/unit-test-system-request-template.md`
  - Brownfield testing-program input. Must more explicitly connect scenario matrix, module waves, and routing policy.
- `templates/testing/coverage-baseline-template.json`
  - Coverage baseline artifact. May need shape tightening for per-module command-tier and hotspot tracking.
- `templates/testing/testing-state-template.md`
  - Resume-state artifact. Must stay state-only while still tracking the richer control-plane fields.

### Shared workflow templates that must consume the control plane

- `templates/commands/test-scan.md`
  - Must define scan outputs and lane synthesis in line with the new artifact boundaries.
- `templates/commands/test-build.md`
  - Must define build outputs, module command tiers, and contract/playbook generation rules in line with the new templates.
- `templates/commands/specify.md`
  - Must treat `UNIT_TEST_SYSTEM_REQUEST.md` as the authoritative brownfield testing-program source.
- `templates/commands/plan.md`
  - Must preserve testing contract, playbook, and coverage baseline semantics in plan artifacts.
- `templates/commands/tasks.md`
  - Must emit test tasks that reflect `small`, `medium`, `fast smoke`, `focused`, and `full` semantics.
- `templates/commands/implement.md`
  - Must make the testing contract and playbook binding at execution time.
- `templates/commands/debug.md`
  - Must preserve repro/regression expectations and canonical validation commands.
- `templates/commands/quick.md`
  - Must consume only bounded module or coverage-wave work from the testing control plane.
- `templates/commands/fast.md`
  - Must stay limited to tiny harness/config/helper repairs and use testing artifacts truthfully.

### Runtime and execution surfaces

- `src/specify_cli/testing_inventory.py`
  - Must produce stronger inventory defaults for Python and TypeScript or JavaScript projects and better command-tier scaffolding inputs.
- `src/specify_cli/execution/packet_compiler.py`
  - Must continue to include testing contract and playbook surfaces in execution packets and may need tighter phrasing if new artifact semantics require it.
- `src/specify_cli/integrations/codex/__init__.py`
  - Generated Codex skills may need assertions to reflect any new shared testing wording.

### Regression tests

- `tests/test_testing_workflow_guidance.py`
  - Main shared behavior lock for testing workflows and artifact templates.
- `tests/test_testing_inventory.py`
  - Runtime inventory behavior lock.
- `tests/test_alignment_templates.py`
  - Broad template contract coverage, including downstream command consumption.
- `tests/test_fast_template_guidance.py`
  - Fast-path routing and test-surface limits.
- `tests/test_quick_template_guidance.py`
  - Quick-path routing and validation expectations.
- `tests/test_debug_template_guidance.py`
  - Regression-test and validation-command expectations in debug flows.
- `tests/test_extension_skills.py`
  - Skill mirror expectations for generated shared skills.
- `tests/integrations/test_integration_codex.py`
  - Generated Codex skill wording and downstream testing workflow propagation.
- `tests/integrations/test_integration_claude.py`
  - Generated Claude integration wording parity.
- `tests/integrations/test_integration_base_markdown.py`
  - Shared Markdown integration propagation.
- `tests/integrations/test_integration_base_skills.py`
  - Shared skills integration propagation.
- `tests/integrations/test_integration_base_toml.py`
  - Shared TOML integration propagation where relevant.

## Task 1: Tighten the downstream testing artifact templates

**Files:**
- Modify: `templates/testing/test-scan-template.md`
- Modify: `templates/testing/test-build-plan-template.md`
- Modify: `templates/testing/test-build-plan-template.json`
- Modify: `templates/testing/testing-contract-template.md`
- Modify: `templates/testing/testing-playbook-template.md`
- Modify: `templates/testing/unit-test-system-request-template.md`
- Modify: `templates/testing/coverage-baseline-template.json`
- Modify: `templates/testing/testing-state-template.md`
- Test: `tests/test_testing_workflow_guidance.py`

- [ ] **Step 1: Write the failing template-guidance tests for artifact boundaries**

```python
def test_testing_artifact_templates_define_distinct_control_plane_roles():
    scan_template = _read("templates/testing/test-scan-template.md").lower()
    build_plan_template = _read("templates/testing/test-build-plan-template.md").lower()
    contract_template = _read("templates/testing/testing-contract-template.md").lower()
    playbook_template = _read("templates/testing/testing-playbook-template.md").lower()
    request_template = _read("templates/testing/unit-test-system-request-template.md").lower()

    assert "fast smoke" in playbook_template
    assert "focused" in playbook_template
    assert "full" in playbook_template
    assert "covered modules" in contract_template or "covered-module" in contract_template
    assert "scenario matrix" in request_template
    assert "local integration seams" in request_template
    assert "module root" in scan_template
    assert "public entrypoints / contracts" in scan_template
    assert "join point" in build_plan_template
```

- [ ] **Step 2: Run the narrow template-guidance test to verify it fails**

Run: `pytest tests/test_testing_workflow_guidance.py -k "distinct_control_plane_roles" -q`
Expected: `FAIL` because the current templates do not yet encode all of the new control-plane wording and command-tier fields.

- [ ] **Step 3: Update `test-scan-template.md` and `test-build-plan-template.md` with stricter artifact roles**

```md
## Module Evidence

### [Module Name]

- Module root:
- Language:
- Framework:
- Covered module status: covered | gap | audit-only
- Risk tier: P0 | P1 | P2 | P3
- Public entrypoints / contracts:
- Truth-owning behavior:
- Candidate layer mix:
  - small:
  - medium:
  - large:
- Candidate command tiers:
  - fast smoke:
  - focused:
  - full:
```

```md
## Waves

### Wave 1: [Name]

- Goal:
- Command tier outcome:
  - fast smoke:
  - focused:
  - full:
- Join point:
  - validation target:
  - validation command:
  - pass condition:
```

- [ ] **Step 4: Update `testing-contract-template.md` and `testing-playbook-template.md` with binding and newcomer-facing command tiers**

```md
## Covered Modules

| Module | Covered Status | Layer Mix | Fast Smoke | Focused | Full | Notes |
|--------|----------------|-----------|------------|---------|------|-------|
| [module] | covered | small + medium | [command] | [command] | [command] | [notes] |

## Mandatory Rules

- Behavior changes in covered modules must add or update tests before implementation is considered complete.
- Bug fixes in covered modules must add regression coverage that would have failed before the fix.
```

```md
## Add New Tests

- Where new tests belong:
- Naming conventions for new test files:
- Shared fixtures, mocks, or factories to reuse:
- Smallest RED-first command to run before implementation:
- Fast smoke command after the first implementation pass:
- Focused module validation command:
- Full project validation command:
```

- [ ] **Step 5: Update `unit-test-system-request-template.md`, `coverage-baseline-template.json`, and `testing-state-template.md` with the new control-plane fields**

```md
## Scenario Matrix

| Scenario ID | Module | Layer | Scenario | Preconditions | Input / Trigger | Expected Observable Outcome | Priority |
|-------------|--------|-------|----------|---------------|-----------------|-----------------------------|----------|
| UT-01 | [module] | small | valid path | [state] | [input] | [observable result] | high |
| UT-02 | [module] | small | invalid / null path | [state] | [input] | [observable result] | high |
| UT-03 | [module] | small | boundary-value path | [state] | [input] | [observable result] | high |
| UT-04 | [module] | medium | local integration seam path | [state] | [input] | [observable result] | medium |
```

```json
{
  "name": "example-module",
  "language": "python",
  "framework": "pytest",
  "baseline_percent": null,
  "target_percent": null,
  "status": "unknown",
  "command_tiers": {
    "fast_smoke": null,
    "focused": null,
    "full": null
  },
  "hotspots": []
}
```

```md
## Coverage Notes

- module:
  - baseline:
  - threshold:
  - command_tiers:
    - fast_smoke:
    - focused:
    - full:
  - exceptions:
  - uncovered_hotspots:
```

- [ ] **Step 6: Run the template-guidance tests and fix any wording mismatches**

Run: `pytest tests/test_testing_workflow_guidance.py -q`
Expected: `PASS` for the new artifact-boundary assertions and no regressions in the existing testing workflow guidance checks.

- [ ] **Step 7: Commit**

```bash
git add templates/testing/test-scan-template.md templates/testing/test-build-plan-template.md templates/testing/test-build-plan-template.json templates/testing/testing-contract-template.md templates/testing/testing-playbook-template.md templates/testing/unit-test-system-request-template.md templates/testing/coverage-baseline-template.json templates/testing/testing-state-template.md tests/test_testing_workflow_guidance.py
git commit -m "feat: tighten downstream testing artifact templates"
```

## Task 2: Update `sp-test-scan` and `sp-test-build` to generate the stricter control plane

**Files:**
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Test: `tests/test_testing_workflow_guidance.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write the failing workflow-guidance assertions for control-plane generation**

```python
def test_test_build_template_requires_command_tier_and_covered_module_outputs():
    content = _read("templates/commands/test-build.md").lower()

    assert "covered modules" in content
    assert "fast smoke" in content
    assert "focused" in content
    assert "full" in content
    assert "local integration seams" in content


def test_test_scan_template_requires_command_tier_discovery():
    content = _read("templates/commands/test-scan.md").lower()

    assert "candidate command tiers" in content or "fast smoke" in content
    assert "covered module status" in content
    assert "local integration seam" in content
```

- [ ] **Step 2: Run the narrow workflow-guidance tests to verify they fail**

Run: `pytest tests/test_testing_workflow_guidance.py -k "command_tier or covered_module" -q`
Expected: `FAIL` because the current workflow templates do not yet require these stronger artifact outputs.

- [ ] **Step 3: Update `templates/commands/test-scan.md` to discover command tiers and covered-module status**

```md
7. **Build module evidence records**
   - For every selected module, record:
     - covered module status: `covered | gap | audit-only`
     - candidate command tiers:
       - `fast smoke`
       - `focused`
       - `full`
     - missing happy-path, invalid-input, boundary, exception, state-transition, and local-integration scenarios
```

```md
9. **Generate scan artifacts**
   - `TEST_SCAN.md` must state candidate layer mix and candidate command tiers per module.
   - `TEST_BUILD_PLAN.md` and `.json` must preserve lane validation commands in a form that later maps cleanly into `fast smoke`, `focused`, or `full` commands.
```

- [ ] **Step 4: Update `templates/commands/test-build.md` to emit covered-module rules and command tiers into the contract/playbook**

```md
11. **Generate durable testing assets**
   - Write `.specify/testing/TESTING_CONTRACT.md` with:
     - covered module status for each module
     - mandatory behavior-change and bug-fix test triggers
     - module-level layer mix
     - project command-tier policy for `fast smoke`, `focused`, and `full`
   - Write `.specify/testing/TESTING_PLAYBOOK.md` with:
     - module-level `fast smoke`, `focused`, and `full` commands
     - where new tests belong for each covered module
     - fixture/helper reuse guidance
```

- [ ] **Step 5: Update the workflow tests to assert the new wording precisely**

```python
assert "covered module status" in _read("templates/commands/test-scan.md").lower()
assert "fast smoke" in _read("templates/commands/test-build.md").lower()
assert "focused" in _read("templates/commands/test-build.md").lower()
assert "full" in _read("templates/commands/test-build.md").lower()
assert "local integration seams" in _read("templates/commands/test-build.md").lower()
```

- [ ] **Step 6: Run the shared testing workflow guidance and alignment tests**

Run: `pytest tests/test_testing_workflow_guidance.py tests/test_alignment_templates.py -q`
Expected: `PASS` with the new command-tier and covered-module assertions preserved alongside the existing scan/build workflow contract checks.

- [ ] **Step 7: Commit**

```bash
git add templates/commands/test-scan.md templates/commands/test-build.md tests/test_testing_workflow_guidance.py tests/test_alignment_templates.py
git commit -m "feat: strengthen test scan and build control plane"
```

## Task 3: Make downstream workflow consumers treat the control plane as binding

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/fast.md`
- Test: `tests/test_testing_workflow_guidance.py`
- Test: `tests/test_fast_template_guidance.py`
- Test: `tests/test_quick_template_guidance.py`
- Test: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Write the failing consumer-workflow assertions**

```python
def test_tasks_template_emits_small_medium_and_command_tier_test_tasks():
    content = _read("templates/commands/tasks.md").lower()

    assert "fast smoke" in content
    assert "focused" in content
    assert "full" in content
    assert "medium" in content
    assert "local integration seams" in content


def test_implement_template_uses_command_tier_language():
    content = _read("templates/commands/implement.md").lower()

    assert "fast smoke" in content
    assert "focused" in content
    assert "full" in content
```

- [ ] **Step 2: Run the narrow consumer-workflow tests to verify they fail**

Run: `pytest tests/test_testing_workflow_guidance.py -k "command_tier_language or small_medium" -q`
Expected: `FAIL` because the downstream consumer workflows do not yet speak in the new command-tier and layer-mix vocabulary.

- [ ] **Step 3: Update `specify.md` and `plan.md` to preserve the stronger brownfield testing inputs**

```md
- Extract module priority waves, covered-module policy, scenario-matrix expectations, `small / medium / large` layer mix, and `fast smoke` / `focused` / `full` validation expectations from `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`.
```

```md
- If `.specify/testing/TESTING_PLAYBOOK.md` exists, preserve the module-level `fast smoke`, `focused`, and `full` commands in the generated planning artifacts.
```

- [ ] **Step 4: Update `tasks.md` to generate test tasks that reflect `small`, `medium`, and command-tier validation**

```md
- Whether or not `.specify/testing/TESTING_CONTRACT.md` exists, treat tests as default deliverables for behavior changes, bug fixes, and refactors.
- If an affected surface is an API, adapter, serializer, CLI boundary, or local integration seam, generate both `small` and `medium` test tasks when the testing contract or testing-program input requires them.
- When the testing playbook exists, preserve `fast smoke`, `focused`, and `full` validation tasks explicitly instead of collapsing everything into one generic test task.
```

- [ ] **Step 5: Update `implement.md`, `debug.md`, `quick.md`, and `fast.md` to consume the same command-tier model**

```md
- `sp-implement`: run the module's `fast smoke` command after the first implementation pass when the playbook defines one, then run `focused`, then `full` when required by the contract.
- `sp-debug`: use the playbook's `focused` and `full` commands after adding repro or regression coverage.
- `sp-quick`: consume one bounded module, one risk tranche, or one coverage wave using the module's existing `fast smoke` / `focused` / `full` command tiers.
- `sp-fast`: stay limited to one tiny harness, command, fixture, or helper repair and use the smallest trustworthy `fast smoke` command.
```

- [ ] **Step 6: Extend the workflow-guidance tests to lock the new consumer semantics**

```python
assert "fast smoke" in _read("templates/commands/implement.md").lower()
assert "focused" in _read("templates/commands/debug.md").lower()
assert "full" in _read("templates/commands/debug.md").lower()
assert "local integration seams" in _read("templates/commands/tasks.md").lower()
assert "coverage wave" in _read("templates/commands/quick.md").lower()
```

- [ ] **Step 7: Run the consumer workflow test suite**

Run: `pytest tests/test_testing_workflow_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py -q`
Expected: `PASS` with the new command-tier wording and no regression in existing routing or validation behavior.

- [ ] **Step 8: Commit**

```bash
git add templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/debug.md templates/commands/quick.md templates/commands/fast.md tests/test_testing_workflow_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py
git commit -m "feat: bind downstream workflows to testing control plane"
```

## Task 4: Strengthen inventory defaults for Python and TypeScript or JavaScript projects

**Files:**
- Modify: `src/specify_cli/testing_inventory.py`
- Test: `tests/test_testing_inventory.py`

- [ ] **Step 1: Write the failing inventory tests for stronger Python and TypeScript or JavaScript defaults**

```python
def test_build_testing_inventory_reports_javascript_command_tier_candidates(tmp_path):
    project = tmp_path / "web"
    project.mkdir()
    (project / "package.json").write_text(
        json.dumps(
            {
                "name": "web",
                "scripts": {
                    "test": "vitest run",
                    "test:unit": "vitest run src",
                    "test:smoke": "vitest run tests/smoke",
                    "coverage": "vitest run --coverage",
                },
                "devDependencies": {"vitest": "^3.0.0"},
            }
        ),
        encoding="utf-8",
    )

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["canonical_test_command"] == "vitest run"
    assert module["command_tiers"]["fast_smoke"] == "vitest run tests/smoke"
    assert module["command_tiers"]["focused"] == "vitest run src"
    assert module["command_tiers"]["full"] == "vitest run"
```

- [ ] **Step 2: Run the inventory tests to verify they fail**

Run: `pytest tests/test_testing_inventory.py -k "command_tier_candidates" -q`
Expected: `FAIL` because the current inventory payload does not expose command-tier candidate fields.

- [ ] **Step 3: Extend `testing_inventory.py` to emit command-tier candidates and stronger defaults**

```python
def _command_tiers(language: str, scripts: dict[str, str], test_command: str | None, coverage_command: str | None) -> dict[str, str | None]:
    if language == "javascript":
        return {
            "fast_smoke": scripts.get("test:smoke") or scripts.get("smoke"),
            "focused": scripts.get("test:unit") or scripts.get("test:focused") or test_command,
            "full": scripts.get("test") or test_command,
        }
    if language == "python":
        return {
            "fast_smoke": "pytest -q",
            "focused": test_command,
            "full": coverage_command or test_command,
        }
    return {"fast_smoke": None, "focused": test_command, "full": coverage_command or test_command}
```

- [ ] **Step 4: Preserve backward compatibility while extending the module payload**

```python
modules.append(
    {
        "module_name": _module_name(module_root, manifest_path, language),
        "module_root": module_root.relative_to(project_root).as_posix() or ".",
        "module_kind": module_kind,
        "language": language,
        "manifest_path": manifest_path.relative_to(project_root).as_posix(),
        "selected_skill": LANGUAGE_SKILL_MAP.get(language),
        "framework": framework,
        "framework_confidence": framework_confidence,
        "canonical_test_path": test_path,
        "canonical_test_command": test_command,
        "coverage_command": coverage_command,
        "command_tiers": _command_tiers(language, scripts, test_command, coverage_command),
        "state": state,
        "classification_reason": classification_reason,
    }
)
```

- [ ] **Step 5: Add a Python inventory test that asserts the default command-tier fallback**

```python
def test_build_testing_inventory_reports_python_command_tier_defaults(tmp_path):
    project = tmp_path / "python-project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1.0'\n[tool.pytest.ini_options]\naddopts=['-q']\n",
        encoding="utf-8",
    )
    (project / "tests").mkdir()
    (project / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    payload = build_testing_inventory(project)
    module = payload["modules"][0]

    assert module["command_tiers"]["fast_smoke"] == "pytest -q"
    assert module["command_tiers"]["focused"] == "pytest"
    assert module["command_tiers"]["full"] == "pytest --cov"
```

- [ ] **Step 6: Run the inventory test file and fix any schema regressions**

Run: `pytest tests/test_testing_inventory.py -q`
Expected: `PASS` with all previous inventory behaviors intact and the new command-tier candidate fields available.

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/testing_inventory.py tests/test_testing_inventory.py
git commit -m "feat: add command tier candidates to testing inventory"
```

## Task 5: Ensure execution packet context preserves the testing control plane

**Files:**
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Test: `tests/execution/test_packet_compiler.py`

- [ ] **Step 1: Write the failing packet-compiler test for testing control-plane context**

```python
def test_compile_worker_task_packet_includes_testing_control_plane_context(tmp_path):
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "specs" / "feature"
    (project_root / ".specify" / "testing").mkdir(parents=True)
    feature_dir.mkdir(parents=True)

    (project_root / ".specify" / "testing" / "TESTING_CONTRACT.md").write_text("# Testing Contract\n", encoding="utf-8")
    (project_root / ".specify" / "testing" / "TESTING_PLAYBOOK.md").write_text("# Testing Playbook\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("## Required Implementation References\n- `src/app.py`\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [ ] T001 [US1] Update tests/test_app.py and src/app.py\n", encoding="utf-8")

    packet = compile_worker_task_packet(project_root=project_root, feature_dir=feature_dir, task_id="T001")

    assert ".specify/testing/TESTING_CONTRACT.md" in packet.scope.read_scope
    assert ".specify/testing/TESTING_PLAYBOOK.md" in packet.scope.read_scope
```

- [ ] **Step 2: Run the packet-compiler test to verify current behavior**

Run: `pytest tests/execution/test_packet_compiler.py -k "testing_control_plane_context" -q`
Expected: `FAIL` only if the richer test surface is not yet preserved clearly enough; otherwise note the existing behavior and tighten assertions to the new semantics before changing code.

- [ ] **Step 3: Update `packet_compiler.py` only if needed to preserve the richer testing-surface purpose strings**

```python
(
    ".specify/testing/TESTING_CONTRACT.md",
    "testing_contract",
    "Project-level testing obligations for covered modules, regression requirements, and command-tier expectations.",
    ["validation", "forbidden_drift"],
    "testing contract constrains what counts as complete",
),
(
    ".specify/testing/TESTING_PLAYBOOK.md",
    "testing_playbook",
    "Canonical fast smoke, focused, and full verification commands plus module-local test placement guidance.",
    ["validation"],
    "testing playbook provides runnable verification commands",
),
```

- [ ] **Step 4: Run the packet compiler tests**

Run: `pytest tests/execution/test_packet_compiler.py -q`
Expected: `PASS`, with the testing control-plane documents clearly preserved in execution packet context.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/execution/packet_compiler.py tests/execution/test_packet_compiler.py
git commit -m "feat: preserve testing control plane in execution packets"
```

## Task 6: Propagate the new testing semantics through generated integrations

**Files:**
- Modify: `src/specify_cli/integrations/codex/__init__.py` only if generated wording requires integration-specific reinforcement
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_codex.py`
- Test: `tests/integrations/test_integration_claude.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/integrations/test_integration_base_toml.py`

- [ ] **Step 1: Write the failing integration assertions for command-tier propagation**

```python
from typer.testing import CliRunner
from specify_cli import app


def test_generated_test_build_skill_mentions_fast_smoke_and_focused_commands(tmp_path):
    runner = CliRunner()
    target = tmp_path / "codex-test-build-control-plane"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    content = (target / ".codex" / "skills" / "sp-test-build" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "fast smoke" in content
    assert "focused" in content
    assert "full" in content
```

- [ ] **Step 2: Run the narrow integration tests to verify they fail**

Run: `pytest tests/integrations/test_integration_codex.py -k "fast_smoke_and_focused" -q`
Expected: `FAIL` because the generated integration content does not yet include the stronger testing semantics end to end.

- [ ] **Step 3: Prefer fixing shared template propagation before touching integration-specific code**

```python
# Only add CodexIntegration augmentation when shared template output still lacks
# required runtime-specific reinforcement after the shared template changes land.
```

- [ ] **Step 4: Update the integration tests to assert the shared testing semantics on generated artifacts**

```python
assert "fast smoke" in test_build_content
assert "focused" in test_build_content
assert "full" in test_build_content
assert "covered modules" in test_build_content
```

- [ ] **Step 5: Run the shared integration regression suite**

Run: `pytest tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q`
Expected: `PASS`, confirming the stronger testing control-plane semantics ship through generated integrations rather than only living in source templates.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/integrations/codex/__init__.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "test: lock generated integrations to testing control plane"
```

## Task 7: Run the full targeted regression sweep and close gaps

**Files:**
- Modify: any files from Tasks 1-6 that still need small repairs after full regression
- Test: `tests/test_testing_workflow_guidance.py`
- Test: `tests/test_testing_inventory.py`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_fast_template_guidance.py`
- Test: `tests/test_quick_template_guidance.py`
- Test: `tests/test_debug_template_guidance.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_codex.py`
- Test: `tests/integrations/test_integration_claude.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/integrations/test_integration_base_toml.py`
- Test: `tests/execution/test_packet_compiler.py`

- [ ] **Step 1: Run the consolidated regression suite**

Run: `pytest tests/test_testing_workflow_guidance.py tests/test_testing_inventory.py tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/execution/test_packet_compiler.py -q`
Expected: `PASS` with no regressions in shared workflow guidance, inventory behavior, execution packet context, or generated integration outputs.

- [ ] **Step 2: If any failures remain, make the smallest contract-preserving fix and rerun the failing subset**

```bash
pytest tests/test_testing_workflow_guidance.py -q
pytest tests/integrations/test_integration_codex.py -q
```

Expected: rerun the exact failing file from the previous suite output using one concrete file command at a time, such as the examples above, until each remaining contract gap moves to `PASS` without broad unrelated rewrites.

- [ ] **Step 3: Run formatting or static checks only if the touched files require them**

Run: `python -m pytest --version`
Expected: confirm the environment is still healthy for the regression suite; do not introduce unrelated lint work unless a touched file or existing CI expectation requires it.

- [ ] **Step 4: Commit**

```bash
git add templates/commands/test-scan.md templates/commands/test-build.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/debug.md templates/commands/quick.md templates/commands/fast.md templates/testing/test-scan-template.md templates/testing/test-build-plan-template.md templates/testing/test-build-plan-template.json templates/testing/testing-contract-template.md templates/testing/testing-playbook-template.md templates/testing/unit-test-system-request-template.md templates/testing/coverage-baseline-template.json templates/testing/testing-state-template.md src/specify_cli/testing_inventory.py src/specify_cli/execution/packet_compiler.py src/specify_cli/integrations/codex/__init__.py tests/test_testing_workflow_guidance.py tests/test_testing_inventory.py tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/execution/test_packet_compiler.py
git commit -m "feat: harden downstream testing control plane"
```

## Self-Review

### Spec coverage

- Single control plane: covered by Tasks 1-3 through artifact-boundary changes and downstream consumer enforcement.
- Newcomer-first usability: covered by Tasks 1-3 through playbook, contract, and command-tier propagation.
- `small + medium + fast smoke` first-release scope: covered by Tasks 1-4 through templates, consumer workflows, and inventory command-tier defaults.
- Python and TypeScript or JavaScript stronger defaults: covered by Task 4.
- Contract-driven automation and runtime reuse: covered by Tasks 2, 4, and 5.
- Integration propagation: covered by Task 6.

### Placeholder scan

- No `TBD`, `TODO`, or “implement later” placeholders remain in the plan.
- Every task has exact file paths, exact commands, and concrete expected outcomes.
- Code-edit tasks include representative code blocks for the intended change shape.

### Type consistency

- The command-tier vocabulary is consistent: `fast smoke`, `focused`, `full`.
- The layer vocabulary is consistent: `small`, `medium`, `large`.
- The brownfield entry artifact remains `UNIT_TEST_SYSTEM_REQUEST.md`.
- The binding downstream policy artifacts remain `TESTING_CONTRACT.md` and `TESTING_PLAYBOOK.md`.
