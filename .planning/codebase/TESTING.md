# Testing Patterns

**Analysis Date:** 2026-04-11

## Test Framework

**Runner:**
- `pytest` via the optional `test` dependency group in `pyproject.toml`
- Config: `pyproject.toml`

**Assertion Library:**
- Native `assert` statements
- `pytest.raises(...)` for exception assertions

**Run Commands:**
```bash
uv sync --extra test      # Install test dependencies
uv run pytest             # Run the full suite
uv run pytest -v          # Verbose run (matches repo defaults)
uv run pytest --cov=src   # Coverage-oriented local run; coverage config lives in pyproject.toml
uvx ruff check src/       # Lint production Python the same way CI does
```

## Test File Organization

**Location:**
- Tests live under `tests/` and are separated by subsystem.
- Use top-level unit-style modules for broad core behavior, for example `tests/test_extensions.py`, `tests/test_presets.py`, and `tests/test_timestamp_branches.py`.
- Use focused subdirectories when fixture scope or subsystem size warrants it:
  - `tests/integrations/` for integration framework and per-agent scaffolding behavior
  - `tests/contract/` for higher-level CLI/API surface guarantees
  - `tests/codex_team/` for Codex team runtime units and smoke tests

**Naming:**
- Name test files `test_<subject>.py`.
- Name test classes `Test<Subject>` when grouping related cases, for example `TestExtensionManifest` in `tests/test_extensions.py` and `TestInitIntegrationFlag` in `tests/integrations/test_cli.py`.
- Name test functions `test_<behavior>` and describe a single invariant.

**Structure:**
```text
tests/
├── conftest.py
├── test_*.py
├── integrations/
│   ├── conftest.py
│   ├── test_integration_base_markdown.py
│   ├── test_integration_base_toml.py
│   └── test_integration_<agent>.py
├── contract/
│   └── test_codex_team_*.py
└── codex_team/
    ├── conftest.py
    └── test_*.py
```

## Test Structure

**Suite Organization:**
```python
class TestInitIntegrationFlag:
    def test_integration_and_ai_mutually_exclusive(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "init", str(tmp_path / "test-project"), "--ai", "claude", "--integration", "copilot",
        ])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output
```

**Patterns:**
- Group related assertions in classes, but rely on function-level isolation rather than `unittest`-style state.
- Use `tmp_path` heavily to build temporary projects, repos, and generated output trees. This is the dominant pattern across `tests/integrations/test_cli.py`, `tests/contract/test_codex_team_generated_assets.py`, and `tests/codex_team/test_tmux_smoke.py`.
- Build reusable mixins for repeated subsystem guarantees instead of copy/pasting per-agent tests. `tests/integrations/test_integration_base_markdown.py` and `tests/integrations/test_integration_base_toml.py` are the key examples.
- Use plain asserts for output, file existence, serialized JSON/TOML content, and path inventories.

## Mocking

**Framework:** `pytest` fixtures plus `monkeypatch`; occasional `unittest.mock.patch`

**Patterns:**
```python
def test_ensure_tmux_available_mentions_psmux_on_native_windows(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    assert "psmux" in str(excinfo.value)
```

```python
with patch.object(Path, "cwd", return_value=project_dir):
    result = runner.invoke(app, ["preset", "set-priority", "test-pack", "5"])
```

**What to Mock:**
- External environment detection and OS tooling, for example `shutil.which`, runtime backend checks, and current working directory.
- Isolated helper lookups such as `load_init_options` when validating caching or invocation translation in `tests/test_extensions.py`.
- Avoid network dependence by building local directories and archives instead of calling remote services.

**What NOT to Mock:**
- Filesystem-heavy workflows that are core to the product. The suite usually creates real files under `tmp_path` and verifies actual generated content.
- CLI behavior. Prefer invoking the real Typer app through `typer.testing.CliRunner` rather than mocking command handlers.
- Template rendering and manifest persistence. Tests usually read the generated files back from disk and assert on concrete output.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def valid_manifest_data():
    return {
        "schema_version": "1.0",
        "extension": {
            "id": "test-ext",
            "name": "Test Extension",
            "version": "1.0.0",
            "description": "A test extension",
        },
        "requires": {"speckit_version": ">=0.1.0"},
        "provides": {"commands": [{"name": "sp.test-ext.hello", "file": "commands/hello.md"}]},
    }
```

**Location:**
- Shared helpers live in `tests/conftest.py`, `tests/integrations/conftest.py`, and `tests/codex_team/conftest.py`.
- Larger subsystems often define local fixtures near the tests that consume them, such as `valid_manifest_data` and `project_dir` in `tests/test_extensions.py`, or `git_repo` and `ps_git_repo` in `tests/test_timestamp_branches.py`.
- Test fixtures commonly build complete throwaway projects on disk rather than using abstract factories.

## Coverage

**Requirements:** No explicit coverage threshold is enforced in CI.

**View Coverage:**
```bash
uv run pytest --cov=src --cov-report=term-missing
```

Coverage configuration in `pyproject.toml` scopes source to `src/` and omits `*/tests/*` and `*/__pycache__/*`.

## Test Types

**Unit Tests:**
- The majority of the suite is unit-level or narrow functional testing against concrete modules.
- Examples: `tests/test_extensions.py`, `tests/test_presets.py`, `tests/integrations/test_manifest.py`, and `tests/codex_team/test_task_ops.py`.

**Integration Tests:**
- Integration tests exercise scaffold generation, manifest tracking, command rendering, and CLI flows against a temporary filesystem.
- The clearest examples are `tests/integrations/test_cli.py`, `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_base_toml.py`, and per-agent files such as `tests/integrations/test_integration_codex.py`.

**Contract Tests:**
- Contract tests lock the public Codex team CLI/API surface and generated assets. Examples: `tests/contract/test_codex_team_cli_surface.py`, `tests/contract/test_codex_team_cli_api_surface.py`, and `tests/contract/test_codex_team_generated_assets.py`.
- Treat these as compatibility tests. Add to `tests/contract/` when you need to freeze a user-facing interface or generated artifact contract.

**E2E Tests:**
- No browser or external-system end-to-end framework is detected.
- The closest equivalents are shell-script and CLI flow tests that run real subprocesses inside temporary repos, especially `tests/test_timestamp_branches.py`.

## Common Patterns

**Async Testing:**
- Not a prominent pattern. No async test framework or coroutine-heavy suite is detected in the current test tree.

**Error Testing:**
```python
with pytest.raises(ValueError, match="Absolute paths"):
    m.record_file("/tmp/escape.txt", "bad")
```

```python
result = runner.invoke(app, ["init", "--here", "--integration", "nonexistent"])
assert result.exit_code != 0
assert "Unknown integration" in result.output
```

Use `pytest.raises(..., match=...)` for library errors and `CliRunner().invoke(...)` result assertions for command-line failures.

## Verification Commands Used By CI

- `.github/workflows/test.yml` runs:
  - `uvx ruff check src/`
  - `uv sync --extra test`
  - `uv run pytest`
- `.github/workflows/lint.yml` runs Markdown linting over repo docs with `markdownlint-cli2`.
- `.github/PULL_REQUEST_TEMPLATE.md` asks contributors to run `uv sync && uv run pytest` and `uv run specify --help` before submitting.

## Practical Rules For Adding Tests

- Put new subsystem tests beside related suites under `tests/`, and prefer a dedicated subdirectory only when the subsystem has its own fixtures or contract boundary.
- Reuse `tmp_path`, `CliRunner`, and real file generation instead of mocking output files.
- If behavior is agent-family specific, extend the existing mixin patterns in `tests/integrations/test_integration_base_markdown.py` or `tests/integrations/test_integration_base_toml.py` rather than duplicating whole suites.
- Add contract tests under `tests/contract/` when the change affects stable CLI output, generated assets, or Codex team API payloads.
- When platform-specific behavior matters, use static assertions plus conditional execution, following `tests/test_timestamp_branches.py` with `pytest.mark.skipif(...)`.

---

*Testing analysis: 2026-04-11*
