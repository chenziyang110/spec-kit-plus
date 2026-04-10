# Data Model: Codex Team Runtime Import

## 1. CodexTeamCapability

- **Purpose**: Represents the Codex-only feature bundle that becomes available after `specify init --ai codex`.
- **Key attributes**:
  - `integration_key`: must equal `codex`
  - `surface_name`: the official `specify` command/skill entry point
  - `runtime_embedded`: whether the imported runtime assets are present
  - `tmux_required`: whether the environment must provide `tmux`
  - `default_enabled`: whether the capability is installed for new Codex projects by default
- **Relationships**:
  - Owns one or more generated Codex-facing assets
  - Depends on one embedded runtime subsystem
  - Is blocked by unsupported environment conditions

## 2. EmbeddedRuntimeSubsystem

- **Purpose**: Represents the imported oh-my-codex-derived runtime that is now maintained inside this repository.
- **Key attributes**:
  - `source_origin`: imported upstream runtime lineage
  - `bridge_layer`: the Python-facing invocation boundary
  - `state_root`: where runtime state is persisted for execution
  - `dispatch_model`: task delivery and worker coordination model
  - `cleanup_contract`: how runtime sessions are terminated and cleaned up
- **Relationships**:
  - Is invoked by the Codex team capability
  - Produces runtime session state and dispatch records

## 3. RuntimeSession

- **Purpose**: Represents one live or completed team execution session.
- **Key attributes**:
  - `session_id`
  - `status`: `created | ready | running | failed | cleaned`
  - `environment_check`: pass/fail result for tmux-capable execution
  - `created_at`
  - `finished_at`
- **Lifecycle notes**:
  - Must not enter `running` unless environment validation passes
  - Must end in either `failed` or `cleaned`

## 4. DispatchRecord

- **Purpose**: Tracks unit task delivery inside a runtime session.
- **Key attributes**:
  - `request_id`
  - `target_worker`
  - `status`: `pending | dispatched | acknowledged | failed | completed`
  - `reason`
  - `created_at`
  - `updated_at`
- **Lifecycle notes**:
  - Must move forward monotonically
  - Failure state must remain inspectable during cleanup

## 5. GeneratedCodexAsset

- **Purpose**: Represents generated files installed into a Codex project to expose the capability.
- **Key attributes**:
  - `path`
  - `asset_type`: `skill | context | helper | manifest`
  - `installed_by_default`
  - `tracked_by_manifest`
- **Relationships**:
  - Belongs to one `CodexTeamCapability`
  - Is recorded by the integration manifest system

## 6. ExistingProjectUpgradePath

- **Purpose**: Captures optional migration support for pre-existing Codex projects.
- **Key attributes**:
  - `supported`: yes/no
  - `blocking_for_release`: always `no` in first release
  - `requires_manual_step`: yes/no
  - `compatibility_notes`
- **Lifecycle notes**:
  - May be absent without failing first-release acceptance
  - Must never override the new-project hard guarantee
