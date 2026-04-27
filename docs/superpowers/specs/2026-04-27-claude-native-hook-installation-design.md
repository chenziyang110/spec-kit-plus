# Claude Native Hook Installation Design

**Date:** 2026-04-27  
**Status:** Approved for implementation  
**Owner:** Codex

## Summary

This design adds a first-class Claude Code native hook installation surface to
`spec-kit-plus`.

The repository already has a shared workflow quality-hook engine under
`src/specify_cli/hooks/` and a mature Codex-native adapter path. What is
missing is the Claude-side bridge that installs hook assets, wires them into
`.claude/settings.json`, and keeps that wiring safe to merge, refresh, and
remove.

The design deliberately does **not** copy GSD's product logic into standalone
Claude hooks. Instead, it introduces thin Claude-native hook adapters that call
the existing shared `specify hook` command surface and translate Claude hook
payloads into the shared engine's event model.

## Goals

- Install Claude-native hook assets into project-local `.claude/hooks/`.
- Merge hook registrations into project-local `.claude/settings.json`.
- Reuse the shared `specify hook` engine for workflow truth and blocking rules.
- Keep the installation manifest-safe so uninstall preserves user-managed files.
- Add targeted tests for install, merge, and adapter behavior.

## Non-Goals

- No global Claude installer in this change.
- No attempt to mirror every GSD hook.
- No duplicate workflow logic outside `src/specify_cli/hooks/`.
- No expansion into non-Claude runtimes in this change.

## Architecture

The implementation adds three layers:

1. **Claude hook assets**
   - Thin scripts under the Claude integration package.
   - Installed into `.claude/hooks/` as tracked integration assets.
   - Each script reads Claude's hook payload from stdin and either returns
     advisory `hookSpecificOutput` or a blocking response.

2. **Shared-hook bridge**
   - The Claude hook scripts invoke `specify hook ...` commands rather than
     embedding workflow rules.
   - This keeps preflight, read guard, prompt guard, context monitor, and
     commit validation inside the canonical shared engine.

3. **Settings merge/install**
   - The Claude integration writes or merges `.claude/settings.json`.
   - Managed registrations are added only when missing.
   - Existing non-managed user hooks and settings are preserved.

## Managed Claude Hook Set

The shipped managed set now covers:

- `SessionStart`
  - shared statusline/orientation context through `specify hook render-statusline`
- `UserPromptSubmit`
  - shared prompt guard through `specify hook validate-prompt`
- `PreToolUse`
  - shared read guard for sensitive path access through
    `specify hook validate-read-path`
  - shared inline commit validation for `git commit -m ...` through
    `specify hook validate-commit`
- `PostToolUse`
  - shared resumable-session drift checks through
    `specify hook validate-session-state` when an active implement/quick/debug
    workflow can be inferred
- `Stop`
  - shared context checkpointing through
    `specify hook monitor-context --trigger before_stop`

## Settings Strategy

The Claude integration should behave like the Copilot integration in terms of
merge safety:

- If `.claude/settings.json` does not exist, create it.
- If it exists and contains valid JSON, merge managed hook registrations.
- If it exists but cannot be parsed, preserve the file and skip hook
  registration with a warning rather than overwriting it.

Managed hook commands should be identifiable by the installed script filenames
so later refresh/uninstall logic can remove only integration-owned entries.

## File Layout

- Create: `.claude/hooks/*.py` or `.claude/hooks/*.sh` through integration setup
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `src/specify_cli/integrations/base.py` only if shared file helpers are
  needed
- Add tests under `tests/integrations/` for Claude install behavior
- Update docs in `README.md` and `docs/quickstart.md`

## Acceptance Criteria

- `specify init --ai claude` creates `.claude/hooks/` assets.
- `specify init --ai claude` creates or merges `.claude/settings.json` with
  managed hook registrations.
- Existing valid user settings are preserved.
- Broken/non-JSON settings are preserved without destructive overwrite.
- Claude integration tests cover install and merge behavior.
- Existing shared hook CLI tests remain green.
