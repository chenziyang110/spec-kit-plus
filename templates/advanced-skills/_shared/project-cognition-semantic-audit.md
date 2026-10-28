# Semantic permission, resume, and final claims


Compass, semantic intake, and graph evidence select bounded routes; they do not
authorize source edits or a final claim. The owning workflow still decides its
write boundary from live evidence and its own stage contract.

When semantic routing affects permission, source-write scope, resume, or a
root-cause, fixed, completed, or release-safe claim, persist
`semantic-audit-input.json` and `semantic-audit-output.json` beside the active
workflow state only through the cognition CLI. Use the deterministic runtime
rather than reconstructing its stable schema:

Build the audit input in memory, run
`{{specify-subcmd:specify-runtime cognition semantic-audit --input-json '<semantic-audit-input-json>' --persist-dir <WORKFLOW_STATE_DIR> --format json}}`.
The runtime atomically writes both registered artifacts; never recreate,
submit, or patch either audit file.

On resume, query those artifacts through `artifact show`, then validate the
persisted route, active claim, authorization refs, and verification refs with:

`{{specify-subcmd:specify-runtime cognition semantic-audit-resume --input-json '<resume-validation-json>' --format json}}`
with an in-memory validation object; never create a resume-validation file.

If either audit file is missing, stale, or inconsistent, do not reuse
`claim_ready`; rerun `semantic-audit --persist-dir` and keep the final claim blocked. A final claim
requires explicit `workflow_authorization` for that claim plus claim-specific
passed verification whose evidence refs match the authorization. Failed,
blocked, skipped, or inconclusive evidence cannot be promoted. Semantic audit
does not authorize source edits, external writes, or a higher permission level;
resume validation grants none of them either. The active SPX workflow remains the owner of those
decisions. If the audit runtime is unavailable, preserve the same evidence and
authorization boundary in workflow state and stay at the lower safe permission;
do not create canonical audit files, and never infer readiness from chat memory
or graph confidence.
