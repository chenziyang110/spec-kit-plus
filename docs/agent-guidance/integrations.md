# Agent Integrations

Read before adding an integration or changing its generated files, invocation,
CLI checks, context updates, or packaging. Code paths below are relative to the
repository root. Also read [Workflow Profiles](workflow-profiles.md) when
profile support or installation membership changes.

## Start With Live Owners

| Concern | Authoritative source |
| --- | --- |
| Supported agents and registration | `src/specify_cli/integrations/__init__.py` (`INTEGRATION_REGISTRY`) |
| Shared generation and skills support | `src/specify_cli/integrations/base.py`, `src/specify_cli/agents.py` |
| Exact directory, format, arguments, CLI requirement, and context file | The integration's `__init__.py` and `registrar_config` |
| User-facing support and invocation matrix | `README.md`, CLI help, and `tests/integrations/test_registry.py` |
| Context updates | Shared Bash/PowerShell context renderers plus `src/specify_cli/integrations/*/scripts/update-context.*` |
| Distribution | `pyproject.toml`, `src/specify_cli/integrations/manifest.py`, package/install tests |

Do not maintain another complete agent list here. Check the registry and the
nearest compatible integration before changing metadata; neither a directory
name nor a historical example proves an integration's current behavior.

## Add or Update an Integration

1. Add `src/specify_cli/integrations/<python_safe_name>/` using the appropriate
   base class, then register it in `INTEGRATION_REGISTRY`. `AGENT_CONFIG` is
   derived from that registry; do not hand-write another agent dictionary in
   `src/specify_cli/__init__.py`.
2. Use the actual executable name as `key` for CLI agents (for example,
   `cursor-agent`, not `cursor`). Check `config.name`, `folder`,
   `commands_subdir`, `install_url`, and `requires_cli`; set `requires_cli` only
   when an executable check is part of the integration's actual contract.
   IDE-only integrations normally use `install_url: None`.
3. Set `registrar_config` for the exact destination, format, argument
   placeholder, extension, and needed transformations. Set `context_file` and
   skills/profile support from the native surface. Ordinary integrations should
   inherit shared rendering rather than add custom `init()` or `check()` branches.
4. Update both `scripts/bash/update-agent-context.sh` and
   `scripts/powershell/update-agent-context.ps1`, together with the integration's
   thin `scripts/update-context.*` wrappers. Cover explicit selection, existing
   file discovery, default creation, help text, and shared context-file aliases.
   Preserve user content outside the managed block.
5. Update `README.md`, registry/help expectations, and relevant examples. Update
   package data/force-includes in `pyproject.toml` if new files must ship. Release
   workflow changes are needed only when release behavior or assets change;
   there is no current `.github/workflows/scripts/create-release-packages.sh`
   or `.github/workflows/scripts/create-github-release.sh`.
6. When devcontainer support is relevant, update `.devcontainer/devcontainer.json`
   for VS Code extensions and `.devcontainer/post-create.sh` for CLI installation.
   Install commands must be non-interactive and work on the configured Linux
   image (Debian Trixie or later); verify the changed setup.
7. Generate an isolated test project with the selected integration/profile and
   inspect the result. Verify exact filenames, invocation, arguments, sidecars,
   context preservation, manifests, CLI checks, and applicable profile coexistence.
   Build the package when package inclusion changes.

## Native Differences to Preserve

- Markdown/prompt templates normally use `$ARGUMENTS`; TOML integrations use
  `{{args}}`; Forge uses `{{parameters}}`. `{SCRIPT}` and `__AGENT__` are renderer
  placeholders. Read the owning registrar instead of inferring syntax from the
  file extension.
- Codex defaults to skills in `.codex/skills/`; it does not require `--ai-skills`.
  Skills destinations and invocations differ by integration. Classic workflow
  skills use `sp-*`, Advanced uses `spx-*`, and Classic passive skills keep their
  template directory names. Preserve the three Advanced-installed Classic map
  companions and do not install the Classic passive bundle into Advanced.
- Copilot owns `.github/agents/*.agent.md`, companion
  `.github/prompts/*.prompt.md`, merged `.vscode/settings.json`, and context at
  `.github/copilot-instructions.md`. Its companion prompts target `agent: sp.<command>`;
  use the current renderer rather than an old `mode:` example.
- Forge's custom setup replaces remaining `$ARGUMENTS`, removes incompatible
  `handoffs` frontmatter, inserts a missing `name`, and installs its reference
  sidecars. Its context wrappers target root `AGENTS.md`.
- Respect exceptions such as `.opencode/command/`, `.tabnine/agent/commands/`,
  Amp's shared `.agents/commands/`, and separate skills/context directories.
  Never derive a destination mechanically from the CLI key.

## Verification

Run the changed integration's suite and `tests/integrations/test_registry.py`.
For shared rendering, include `tests/integrations/test_integration_base_skills.py`;
for context changes, include `tests/test_agent_context_managed_block.py` and
`tests/test_agent_config_consistency.py`. Add profile, packaging, and install
coverage when those surfaces change. Generated assets are verification outputs;
repair templates/renderers and regenerate instead of editing the outputs.
