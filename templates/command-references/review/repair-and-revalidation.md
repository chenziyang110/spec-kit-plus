Trigger: when a required scenario fails, a blocking diagnostic appears, or consumer wiring is incomplete.

Purpose: turn system-review findings into bounded repairs with exact proof, while routing upstream truth and unknown mechanisms to their proper owners.

## Finding And Repair Loop

Record the expected behavior, observed behavior, scenario id, sanitized evidence, classification, affected scope, suspected owner, status, and exact next action before editing.

- Clear, bounded, approved-scope implementation defect: repair inside `sp-review`, add or strengthen regression coverage, and record changed paths.
- Unknown root cause, intermittent mechanism, or diagnosis requiring exploration: preserve the exact failed scenario, hand off to `{{invoke:debug}}`, and stop. Resume Review at that scenario after Debug returns evidence.
- Large missing approved implementation: reopen `sp-implement` and stop.
- Missing or invalid task graph: reopen `sp-tasks` and stop.
- Architecture/plan defect: reopen `sp-plan`; requirement or scope truth defect: route to `sp-clarify`/`sp-specify`; missing approved design truth: route to `sp-design`.
- Human/external authority, credentials, protected service, physical device, or unavailable comparison: persist a structured blocker and full Human Action Guide with observable unblock criteria and exact Review resume point.

After every repair, restart the official real entrypoint when process/configuration state may be affected. Rerun the exact failed action sequence, all scenarios depending on the repaired surface, and the smallest credible regression set. A source diff, unit test, or worker assertion alone cannot resolve the finding. Close it only with fresh required evidence and a passing revalidation result.
