# Team runtime boundary

The supported entrypoint is the project launcher-backed `sp-teams` command, not
an agent alias or a manually edited `.specify/teams/` file. Inspect command help
before using an unfamiliar operation.

Status and doctor are read-only. Live probe may create transient runtime state.
Dispatch, sync-back, resume, shutdown, and cleanup mutate durable coordination
state and require an explicit operational reason. Cleanup is never a repair for
an active or blocked batch whose results still matter.

Runtime health proves coordination capability, not task correctness. Feature
acceptance, joins, repository verification, and implementation closeout remain
owned by `spx-implement-teams`.
