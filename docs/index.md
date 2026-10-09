# Spec Kit Plus

Spec-Driven Development for local AI coding agents: carry product intent through
implementation, integrated review and human acceptance without losing state.

## Start with your goal

You do not need to learn the whole workflow catalog before starting.
[Start Here](start-here.md) explains setup and the first interaction.

| What you need now | Existing workflow | Boundary |
| --- | --- | --- |
| Understand the repository | `ask` | Read-only, evidence-backed answers |
| Shape an idea | `discussion` | Clarify intent before choosing delivery |
| Deliver an already-clear outcome | `quick` | Resumable direct delivery; not limited to small tasks |
| Build a formal specification | `specify` | Start the formal artifact and acceptance chain |
| Continue unfinished work | `auto` | Resume an existing, unambiguously bound state; never guess a new task |

These are canonical workflow names, not shell commands. Your selected Agent
integration determines whether invocation uses `$sp-*`, `/sp-*`, `/skill:sp-*`
or `/sp.*`. Use the exact Start Here panel printed by `specify init`.

## Delivery paths

The normal formal route is `specify -> plan -> tasks -> implement -> review -> accept`.
Substantive UI without an applicable registered design uses the conditional
`specify -> design -> plan` gate. Design approval remains user-owned.
Feasibility research and Test Design are conditional branches, not universal
extra steps. Quick is a different delivery path, not permission to skip evidence.

## Installation, upgrade and recovery

| Goal | Guide |
| --- | --- |
| Install and pin a compatible CLI/runtime | [Installation](installation.md) |
| Complete a first workflow | [Quick Start](quickstart.md) |
| Upgrade or repair generated assets | [Upgrade](upgrade.md) |
| Diagnose tools and installed project compatibility | Run `specify check` |
| Investigate missing or failing CI evidence | [CI troubleshooting](ci-troubleshooting.md) |

An untagged Git installation follows development head. Prefer an explicitly
selected published source tag for reproducible use. Source access is required
for private Git installs; public runtime binaries do not make the source public.

## Maintainer and reference documentation

- [Local Development](local-development.md): source setup and verification.
- [Project Handbook](../PROJECT-HANDBOOK.md): architecture and product contracts.
- [Repository Guidance](../AGENTS.md): source ownership and change propagation.
- [Workflow Profiles](agent-guidance/workflow-profiles.md): separate Classic and Advanced prompt products over shared runtime contracts.
- [Constitution Profiles](constitution-profiles.md): governance defaults.
- [Asset Governance](asset-governance.md): passive document/media placement, exact-change checks, optional catalogs and guarded migration.
- [Cognition Compatibility](project-cognition-compatibility-inventory.md): navigation compatibility; live source remains authoritative.
- [Workflow Quality](workflow-quality/README.md): measure full-chain cost and retained behavior; a target is not an achieved metric.

The [repository README](../README.md) retains the extended command/reference
material. Product questions and reproducible defects belong in the
[private repository issue tracker](https://github.com/chenziyang110/spec-kit-plus/issues).
