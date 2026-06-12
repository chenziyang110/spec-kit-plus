# Current sp-* Workflow Prompt Cost Baseline

## Scope

This baseline measures prompt-source cost for the current SuperSpec workflow surfaces:

- `templates/commands/*.md`
- `templates/command-partials/**/*.md`
- `templates/passive-skills/**/SKILL.md`
- `templates/worker-prompts/*.md`

It does not score quality. Quality scoring requires Behavior-Artifact Backtrace against real downstream samples.

## Metrics Command

```powershell
uv run python tools\workflow-quality\measure_workflow_costs.py --root . --format markdown
```

## Current Totals

# Workflow Cost Metrics

## Totals

| Kind | Files | Lines | Words | Bytes |
| --- | ---: | ---: | ---: | ---: |
| prompt | 103 | 21487 | 150294 | 1134186 |

## Interpretation

- This baseline is a cost baseline, not a quality baseline.
- Future workflow prompt changes should record prompt reduction against this baseline or a workflow-specific baseline.
- A prompt reduction is acceptable only when the related quality retention score remains at or above 98%.

## Next Baselines

- Add artifact-cost baselines from a copied or locally available downstream sample set such as `F:\AI_WORK\jx-skills`.
- Add workflow-specific baselines for the first pilot workflow before changing that workflow.
