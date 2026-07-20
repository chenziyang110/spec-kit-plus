Trigger: when a required scenario fails, a blocking diagnostic appears, or consumer wiring is incomplete.

Purpose: turn system-review findings into bounded repairs with exact proof, while keeping unknown mechanisms under Review ownership and routing only proven upstream truth gaps to their proper owners.

## Finding And Repair Loop

Record the expected behavior, observed behavior, scenario id, sanitized evidence, classification, affected scope, suspected owner, status, and exact next action before editing.

- Every approved-scope defect is Review-owned regardless of repair size. Missing code, a task omission, incomplete tests, broken wiring, and registration/configuration defects are not upstream truth gaps; the Leader decomposes them into one or more bounded Fix packets.
- An unknown root cause or intermittent mechanism remains inside Review. Preserve the exact failed scenario and dispatch a read-only diagnostic packet; Review remains the stage owner, accepts or rejects the diagnosis, and then compiles the Fix wave.
- Only a proven upstream truth gap is a handoff-and-stop boundary: missing or contradictory requirement truth routes to `sp-clarify`/`sp-specify`, missing or contradictory design truth routes to `sp-design`, and architecture truth that must change before any conforming fix is possible routes to `sp-plan`.
- Human/external authority, credentials, protected service, physical device, or unavailable comparison: persist a structured blocker and full Human Action Guide with observable unblock criteria and exact Review resume point.

After the audit join, run a separate Fix wave with finding-bound write scopes. After every repair, restart the official real entrypoint when process/configuration state may be affected. Run an independent revalidation wave over the exact failed action sequence, all scenarios depending on the repaired surface, and the smallest credible regression set. A repair author must not verify its own finding; use the Leader or a different read-only subagent. A source diff, unit test, or worker assertion alone cannot resolve the finding. Close it only with fresh required evidence and a passing revalidation result.
