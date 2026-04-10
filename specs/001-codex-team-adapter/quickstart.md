# Quickstart: Codex Team Runtime Import

## Goal

Validate the first-release Codex-only team/runtime import from a fresh project path and confirm non-Codex isolation.

## Prerequisites

- A tmux-capable environment
- Python 3.11+
- The local `specify` CLI checkout or installed development build
- Codex CLI available when validating generated skills

## Scenario A: Fresh Codex project

1. Create a fresh project with Codex integration:

   ```powershell
   specify init fresh-codex-team --ai codex --ignore-agent-tools
   ```

2. Confirm Codex assets were generated in the expected Codex-owned locations.
   - Confirm `.agents/skills/sp-team/SKILL.md` exists.
   - Confirm `.specify/codex-team/runtime.json` and `.specify/codex-team/README.md` exist.

3. Confirm the new `specify`-owned team entry point is discoverable from the initialized project.
   - Treat `specify team` as the supported product surface.
   - Do not treat `omx` or `$team` as release acceptance surfaces for this repository.

4. In a tmux-capable environment, run the smallest supported team bootstrap flow.

5. Verify all of the following:
   - team bootstrap succeeds
   - a minimal task can be dispatched
   - runtime/session state is recorded
   - a forced or synthetic failure path reports clearly
   - cleanup completes without leaving the session in an ambiguous state

## Scenario B: Non-Codex isolation

1. Create a second project with a non-Codex integration:

   ```powershell
   specify init fresh-claude-no-team --ai claude --ignore-agent-tools
   ```

2. Confirm the Codex-only team/runtime assets are not generated.
   - `.agents/skills/sp-team/SKILL.md` must be absent.
   - `.specify/codex-team/` must be absent.

3. Confirm the `specify`-owned team entry point is not advertised as available for this integration.
   - Help and init messaging must not tell non-Codex projects to use `specify team`.

## Scenario C: Existing Codex project upgrade (optional, non-blocking)

1. Start from an existing Codex project.
2. Apply the optional upgrade path if one exists.
3. Record outcomes as migration evidence, but do not treat failure here as a first-release blocker.
4. Keep release sign-off tied to fresh Codex installs plus non-Codex isolation, not to optional migration coverage.

## Latest Verification

Feature-focused regression bundle used during implementation:

```powershell
pytest tests/contract/test_codex_team_cli_surface.py tests/contract/test_codex_team_generated_assets.py tests/integrations/test_integration_codex.py tests/integrations/test_cli.py tests/integrations/test_integration_subcommand.py tests/test_agent_config_consistency.py tests/integrations/test_registry.py tests/codex_team -q
```

Current result: all selected Codex/team contract, integration, registry, and runtime tests passed in the implementation workspace.
