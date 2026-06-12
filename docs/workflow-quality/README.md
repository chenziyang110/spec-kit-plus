# SP Workflow Compact Quality Standard

## Objective

Optimize `sp-*` workflow prompts and intermediate artifacts by maximizing cost reduction while preserving at least 98% of baseline quality.

```text
maximize prompt and intermediate-artifact cost reduction
subject to quality retention >= 98%
```

This standard applies before changing source command templates under `templates/commands/*.md` (the source for generated `sp-*` workflow commands; downstream or generated install surfaces may refer to these as `templates/commands/sp-*`), `templates/command-partials/**`, `templates/worker-prompts/**`, `templates/passive-skills/**`, `skill-flow-maps/**`, generated workflow artifact contract, handoff shape, state file, task packet format, validation closeout surface, or other handoff/artifact formats.

## Non-Goals

- This is not a rewrite mandate for existing workflows.
- This is not a license to remove guardrails without artifact evidence that the protected behavior remains covered.
- This is not a style-only cleanup rubric; cosmetic edits alone do not justify prompt or artifact contract churn.

## Required Principle

Shorter is not automatically better. A change is accepted only when it reduces whole-chain cost without moving ambiguity, evidence gathering, or interpretation burden downstream.

## Required Evaluation Layers

| Layer | Examples | Required Question |
| --- | --- | --- |
| Prompt | command templates, partials, passive skills | Does this text cause a concrete behavior? |
| Handoff | handoff Markdown/JSON, plan contract, task handoff | Can the next workflow consume this quickly and safely? |
| Planning artifacts | spec, alignment, context, plan, tasks, task packets | Did upstream intent become executable and verifiable work? |
| Execution evidence | quick/debug state, worker results, validation closeout | Did completion evidence prove acceptance and preserve residual risk? |

## Quality Score

| Dimension | Points |
| --- | ---: |
| Behavior correctness | 20 |
| Intent preservation | 15 |
| Evidence quality | 15 |
| Handoff consumability | 15 |
| Downstream executability | 15 |
| Validation closure | 15 |
| Residual risk handling | 5 |

Candidate quality must satisfy this hard gate:

```text
candidate_quality_score / baseline_quality_score >= 0.98
```

If the baseline quality score is below 90, the candidate must also improve the absolute score.

## Cost Metrics

- Prompt cost: lines, words, estimated tokens, repeated rules, authority surfaces.
- Handoff cost: lines, fields, MP/CA count, duplicate sections, blocker clarity, downstream read time.
- Artifact cost: spec/plan/tasks/task packet size, repeated metadata, fields with no consumer.
- Cognitive cost: time to find goal, boundary, blockers, validation, and next action.
- Maintenance cost: number of places a rule must be changed.
- Downstream correction cost: extra fixes, rework, clarification loops, or validation reruns caused by missing upstream guidance.

## Decision Labels

Use exactly these labels when classifying each candidate unit:

- `KEEP`: preserve as-is because it protects required behavior or evidence.
- `COMPRESS`: shorten while preserving the same authority and consumer-visible behavior.
- `MERGE`: combine duplicate or overlapping rules without losing distinct obligations.
- `PARAMETERIZE`: replace repeated specific text with a reusable pattern, variable, or reference.
- `DELETE`: remove only when no consumer, guardrail, artifact field, or validation behavior depends on it.
- `ESCALATE`: stop local optimization and seek review because quality, ownership, or downstream impact is unclear.

## Required Workflow Before Optimizing

1. Measure baseline prompt and artifact costs.
2. Trace each candidate prompt or artifact unit to its protected behavior and consumer.
3. Score baseline quality using real samples when available.
4. Propose candidate changes with one decision label per unit.
5. Test candidate behavior against artifacts, handoffs, skill-flow maps, and sample preservation.
6. Report quality retention, absolute score movement, cost reduction, downstream correction cost, and residual risk.

Protocol summary: baseline, trace, score, propose, test, report.

## Related Files

- Design: `docs/superpowers/specs/2026-06-12-sp-workflow-compact-quality-standard-design.md`
- Pattern catalog: `docs/workflow-quality/reusable-pattern-catalog.md`
- Evaluation template: `docs/workflow-quality/evaluation-record-template.md`
- Metrics utility: `tools/workflow-quality/measure_workflow_costs.py`
