# Start Here

## Install a known version

Use Python 3.11 or newer, uv, and your selected agent CLI or IDE. If Git asks
you to sign in, use your existing Git credentials.

This example pins the `v0.8.8` source tag. Find available versions on the
[release list](https://github.com/chenziyang110/spec-kit-plus-releases/releases)
and other setup options in the [installation guide](installation.md).

```bash
uv tool install specify-cli --from "git+https://github.com/chenziyang110/spec-kit-plus.git@v0.8.8"
specify init my-project --ai codex --workflow-profile classic
cd my-project
specify check
```

For Antigravity, use `--ai agy` and invoke Classic skills with `/sp-*` in the
IDE. New Codex and Antigravity installs put generated skills in `.agents/skills/`.

Classic is the explicit, broadly compatible profile. Advanced is an explicit
opt-in for skills-based integrations. They share runtime contracts but retain
independent prompts; Advanced is not a lower-verification mode.

For an already initialized project, follow the [upgrade guide](upgrade.md) to
repair managed assets or migrate the installed skill layout.

## Pick one outcome

The examples below are entered inside Codex, not a shell. Other integrations
use the invocation shown in their generated Start Here panel.

| Intent | Codex Classic example |
| --- | --- |
| Learn how this project works | `$sp-ask Explain the login path using current code evidence.` |
| Develop an idea | `$sp-discussion Help shape an offline-first wardrobe application.` |
| Deliver a clear change directly | `$sp-quick Add a bounded configuration option and verify its behavior.` |
| Start a formal feature | `$sp-specify Add a searchable knowledge base with an audit trail.` |
| Resume an existing task | `$sp-auto` |

Quick is not limited by task size. Choose formal work when an explicit,
reviewable specification chain is needed. Auto resumes recorded state; it does
not choose a new project or guess between multiple unfinished tasks.

The formal chain remains `specify -> plan -> tasks -> implement -> review -> accept`.
Follow a conditional Design or research gate when the current contract requires
it. Automated tests do not replace integrated Review or human acceptance.

## Understand a stop before doing more work

Read four things in the current workflow's response: selected task, current
stage, exact blocker and owner, and exact resume action. Do not infer completion
from a short status label or manually edit state files to clear a blocker.
Agent-owned recoverable defects stay with the Agent. Human design approval,
external credentials and product acceptance stay with the authorized human.

For installation identity, use `specify version`, `specify --help` and
`specify check`. On Windows, `Get-Command specify -All` locates competing
entrypoints. A `.dev0` package version alone does not identify a commit; keep the
selected source tag/commit and project-local runtime identity in bug reports.
Never add credentials to those reports.

For failed Actions with no steps or logs, use [CI troubleshooting](ci-troubleshooting.md).
Do not disable tests, change repository visibility or declare success to bypass
an infrastructure blocker.
