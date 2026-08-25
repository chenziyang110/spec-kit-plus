This is the conditional, independent UI Confirmation state shared by Quick and
Debug. Its human rendering is one readable `界面方向` section inside the main
checkpoint, not a second approval table. UI applicability includes any
user-visible screen, component, layout, navigation or interaction flow, visual
state, responsive behavior, desktop or mobile surface, accessibility
presentation, TUI layout, or CLI presentation. It does not require an external image.

Quick uses this card for an implementation proposal: the user confirms the
intended experience before implementation. Debug uses this card for a target baseline:
the reporter confirms what the affected experience should be. The
card must not pre-approve a speculative fix or root-cause theory.

Render this section only when every field can be grounded in an approved
project design direction, an inspectable current product surface, or supplied
source material. An unregistered draft or legacy bootstrap seed is not an
approved visual direction. For a new or high-visibility direction, first route
to `sp-design`/`spx-design` and obtain an inspectable visual artifact.
Do not render an incomplete UI Confirmation as if it were approval-ready.

Preserve original references rather than replacing them with prose. For each
reference, state its reference intent, such as preserve, adapt, or inspiration.
Name the real content and image sources that will be exercised; placeholder-only
content is not an adequate acceptance basis.

```markdown
## 界面方向

[Quick implementation proposal or Debug target baseline, plus affected surface]

- **使用者与主要任务**：[user, context, and single job]
- **目标体验**：[visual, content, and interaction thesis plus signature element]
- **可见变化**：[hierarchy, layout, components, copy, and before-to-after]
- **必须保留**：[non-negotiable patterns or behavior]
- **可以调整**：[implementation-flexible details]
- **不得改变**：[visual, content, or interaction regressions]
- **确认依据**：
  - 设计来源：[approved direction/current entry point/original references with
    intent/real content and images]
  - 注册设计绑定：[Quick adoption only: exact scope, `design_change_id`,
    `design_change_ref`, `design_change_sha256`, and `design_contract_ref`]
  - 交互与适配：[input, focus, feedback, state, recovery, responsive, and
    accessibility expectations]
  - 验收方式：[real entry point, risk-based matrix, structure snapshot, visual
    capture, runtime diagnostics, comparison or explicit human review]
```

Keep all corresponding `ui_confirmation` fields in machine state even though
the human labels are shorter. Do not add a second reply prompt: a single confirmation covers both
the main checkpoint and this UI decision, while a
correction may target only the UI fields. For Quick adoption, stage the exact
five-field `decision.ui_confirmation.design_binding` before
`checkpoint-confirm`; never infer or replace it afterward.
