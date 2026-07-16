# Code Quality Reviewer Prompt Template

Legacy compatibility/helper snippet. Ordinary `sp-implement` task review uses
`.specify/templates/worker-prompts/task-reviewer.md`, which returns both
`spec_verdict` and `quality_verdict` in one result. Use this split quality
reviewer helper only for older downstream workflows or special migration/debug
scenarios that intentionally do not use the single task reviewer.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

```
Task tool (native reviewer subagent):
  Use template at .specify/templates/worker-prompts/code-quality-reviewer.md

  WHAT_WAS_IMPLEMENTED: [from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan-file]
  BASE_SHA: [commit before task]
  HEAD_SHA: [current commit]
  DESCRIPTION: [task summary]
```

**In addition to standard code quality concerns, the reviewer should check:**
- Does each file have one clear responsibility with a well-defined interface?
- Are units decomposed so they can be understood and tested independently?
- Is the implementation following the file structure from the plan?
- Did this implementation create new files that are already large, or significantly grow existing files? (Don't flag pre-existing file sizes — focus on what this change contributed.)

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment
