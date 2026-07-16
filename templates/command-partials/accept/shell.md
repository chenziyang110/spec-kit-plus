{{spec-kit-include: ../common/user-input.md}}

## Objective

Guide a contextless human through accepting completed product behavior and keep the conversation resumable from `FEATURE_DIR/human-acceptance.json`.

## Process

## Intake and Freshness

- Resolve the feature with `{SCRIPT}` or lane state; stop on an uncertain or ambiguous lane.
- Transition from the validated `implement` stage into `accept` through the deterministic workflow runtime before any acceptance-owned write.
- Run `{{specify-subcmd:accept prepare --feature-dir <feature-dir> --format json}}`. This creates the deterministic state skeleton after implementation closeout or reports that the existing guide is stale/conflicting.
- Read `implementation-summary.md`, `human-acceptance.json`, the relevant acceptance requirements, and the real user entrypoint. Use code/test evidence only to prepare accurate instructions; do not ask the human to understand it.
- Validate runtime-owned phase state with `{{specify-subcmd:hook validate-state --command accept --feature-dir <feature-dir> --format json}}`.

## Zero-Context Reset

Before asking the human to do anything, give them a compact reset:

- what was added or changed;
- what user problem it solves;
- what they will personally verify;
- prerequisites and exact starting entrypoint;
- what is intentionally outside this acceptance.

Use product words and concrete labels. Do not assume they remember the feature name, branch, commands, architecture, prior decisions, or the last conversation.

## Guided Conversation

- Lead one scenario and one step at a time. Do not present the entire procedure as homework unless the human explicitly asks for a printable checklist.
- For the current step, state the exact click path or command, explain placeholders, state the expected visible result, and state the safe failure branch.
- End with one tiny response request such as “回复 `看到了`；如果没有，发当前画面或报错文本（不要发密钥）”.
- Interpret the human's natural reply, update the current step result/evidence and scenario verdict, move the cursor, then present the next step.
- On resume, restate only the accepted context and the exact current step; do not replay completed steps unless implementation evidence changed.

## Verdict Rules

- `accepted`: every required scenario is explicitly `pass`, `overall.verdict` is `pass`, and the human has made the final acceptance decision.
- `rejected`: at least one observed required behavior fails and the finding records expected, observed, evidence, and repair route.
- `blocked`: the next required observation cannot be performed; preserve the cursor and provide a self-contained Human Action Guide when the boundary is genuinely human-owned.
- Automated tests, agent visual inspection, implementation closeout, or silence from the human never substitute for human PASS.

## Output Contract

- Keep `human-acceptance.json` schema-valid, fresh against implementation evidence, and sufficient to resume from the exact current step.
- The visible reply restores only the context needed now, gives one current action and expected result, and asks for one minimal human observation.
- Final output records accepted, rejected, or blocked honestly and names the exact next workflow without invoking it.

## Guardrails

- Allowed: `FEATURE_DIR/human-acceptance.json` and acceptance-owned `workflow-state.md` fields.
- Forbidden: production source, tests, `spec.md`, planning/task artifacts, implementation lifecycle records, commits, pushes, deployments, external writes, and silent cross-workflow fixes.
- Every failure route is handoff-and-stop. Preserve the acceptance finding and exact resume point so the repair workflow can return to the failed scenario instead of restarting the whole feature.

{{spec-kit-include: ../common/blocker-resolution.md}}
