# sp-* Workflow Compact Quality Standard

## Objective

Optimize `sp-*` workflow prompts and intermediate artifacts by maximizing cost reduction while preserving at least 98% of baseline quality.

```text
maximize prompt and intermediate-artifact cost reduction
subject to quality retention >= 98%
```

This standard applies before changing any `templates/commands/**`, `templates/command-partials/**`, `templates/passive-skills/**`, generated workflow artifact contract, handoff shape, state file, task packet format, or validation closeout surface.

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

Candidate quality must satisfy:

```text
candidate_quality_score / baseline_quality_score >= 0.98
```

## Cost Metrics

- Prompt cost: lines, words, estimated tokens, repeated rules, authority surfaces.
- Handoff cost: lines, fields, MP/CA count, duplicate sections, blocker clarity, downstream read time.
- Artifact cost: spec/plan/tasks/task packet size, repeated metadata, fields with no consumer.
- Cognitive cost: time to find goal, boundary, blockers, validation, and next action.
- Maintenance cost: number of places a rule must be changed.

## Required Workflow Before Optimizing

1. Measure baseline prompt and artifact costs.
2. Score baseline quality using real samples when available.
3. Run Behavior-Artifact Backtrace for candidate prompt or artifact units.
4. Identify keep, merge, move, tighten, and delete candidates.
5. Define replacement protection for every removed or moved rule.
6. Estimate candidate quality retention and cost reduction.
7. Apply only after review approval.
8. Validate tests, skill-flow maps, and sample artifact preservation.
9. Record the evaluation result.

## Related Files

- Design: `docs/superpowers/specs/2026-06-12-sp-workflow-compact-quality-standard-design.md`
- Pattern catalog: `docs/workflow-quality/reusable-pattern-catalog.md`
- Evaluation template: `docs/workflow-quality/evaluation-record-template.md`
- Metrics utility: `tools/workflow-quality/measure_workflow_costs.py`
