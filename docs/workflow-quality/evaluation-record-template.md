# sp-* Workflow Compactness Evaluation Record

## Summary

- workflow:
- target_layer:
- optimization_goal:
- protected_quality:
- decision: proposed | accepted | rejected | needs-revision

## Baseline Metrics

- baseline_prompt_cost_lines:
- baseline_prompt_cost_words:
- baseline_artifact_cost_lines:
- baseline_artifact_cost_words:
- baseline_quality_score:
- baseline_samples:

## Candidate Metrics

- candidate_prompt_cost_lines:
- candidate_prompt_cost_words:
- candidate_artifact_cost_lines:
- candidate_artifact_cost_words:
- candidate_quality_score:
- quality_retention:
- prompt_reduction:
- artifact_reduction:

## Behavior-Artifact Backtrace

| Unit ID | Source Location | Intended Behavior | Artifact Trace | Failure Mode Prevented | Cost | Duplication | Score | Decision | Rationale |
| --- | --- | --- | --- | --- | ---: | --- | ---: | --- | --- |
| EX-001 | templates/commands/example.md:1 | Preserve handoff readiness gate | FEATURE_DIR/handoff-to-tasks.json | Downstream execution starts without required evidence | 12 lines | overlaps with validation closeout | 4 | COMPRESS | Keep gate, shorten duplicate wording |

## Replacement Protection

| Removed or Moved Content | Replacement Protection | Validation |
| --- | --- | --- |
|  |  |  |

## Validation Plan

- Static contract checks:
- Artifact contract checks:
- Efficiency checks:
- Sample chains inspected:

## Result

- quality_retention_passed:
- cost_reduction_passed:
- downstream_cost_not_transferred:
- accepted_changes:
- rejected_changes:
- follow_up:
