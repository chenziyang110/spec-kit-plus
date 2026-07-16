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
- absolute_score_movement:
- prompt_reduction:
- artifact_reduction:
- downstream_correction_cost_baseline:
- downstream_correction_cost_candidate:
- transferred_burden_checked:
- downstream_consumer_impact:

## Quality Dimension Scores

| Dimension | Max Points | Baseline | Candidate | Delta | Evidence |
| --- | ---: | ---: | ---: | ---: | --- |
| Behavior correctness | 20 |  |  |  |  |
| Intent preservation | 15 |  |  |  |  |
| Evidence quality | 15 |  |  |  |  |
| Handoff consumability | 15 |  |  |  |  |
| Downstream executability | 15 |  |  |  |  |
| Validation closure | 15 |  |  |  |  |
| Residual risk handling | 5 |  |  |  |  |

## Behavior-Artifact Backtrace

| Unit ID | Source Location | Unit Text Summary | Intended Behavior | Artifact Trace | Failure Mode Prevented | Cost Level | Duplication Status | Verification Surface | Score | Decision | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| EX-001 | templates/commands/example.md:1 | Handoff readiness gate | Preserve handoff readiness gate | FEATURE_DIR/handoff-to-tasks.json | Downstream execution starts without required evidence | medium | overlaps with validation closeout | tests/test_alignment_templates.py | 4 | COMPRESS | Keep gate, shorten duplicate wording |

## Replacement Protection

| Removed or Moved Content | Replacement Protection | Validation |
| --- | --- | --- |
|  |  |  |

## Validation Plan

- Static contract checks:
- Artifact contract checks:
- Efficiency checks:
- Sample chains inspected:

| Sample | Layers Covered | Baseline Behavior | Candidate Behavior | Regression Found | Evidence | Residual Gap |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Result

- quality_retention_passed:
- cost_reduction_passed:
- downstream_cost_not_transferred:
- transferred_burden_checked:
- downstream_consumer_impact:
- accepted_changes:
- rejected_changes:
- follow_up:
