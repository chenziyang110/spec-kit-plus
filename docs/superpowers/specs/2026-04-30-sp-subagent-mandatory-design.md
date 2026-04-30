# sp-* Subagent Mandatory Design

Date: 2026-04-30
Status: Approved for implementation planning

## Goal

所有 `sp-*` 相关工作流的实质性任务默认且必须使用 subagent 执行。

本设计把这条规则统一到普通 `sp-*` command 模板、被动技能、集成注入文案、项目文档、运行时编排模型和测试断言中。主代理在这些流程中承担编排职责：路由、任务拆分、任务包准备、subagent 派发、等待交付、结果整合、验证和状态更新。

## Scope

覆盖普通 `sp-*` 工作流及其生成面：

- `templates/commands/*.md` 中的普通 `sp-*` command 模板
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- integration 生成和注入文案
- orchestration policy/model 中用于描述 `sp-*` 执行编排的状态词
- README、AGENTS、PROJECT-HANDBOOK 和 project-map 文档
- 相关模板、集成、orchestration、Codex guidance 测试

`sp-teams` 相关语义只归 `sp-implement-teams` / team surface 使用，不作为普通 `sp-*` 工作流文案的一部分。

## Command Coverage

普通 command 模板都需要统一表达 subagent mandatory 规则：

- `templates/commands/analyze.md`
- `templates/commands/auto.md`
- `templates/commands/checklist.md`
- `templates/commands/clarify.md`
- `templates/commands/constitution.md`
- `templates/commands/debug.md`
- `templates/commands/deep-research.md`
- `templates/commands/explain.md`
- `templates/commands/fast.md`
- `templates/commands/implement.md`
- `templates/commands/map-build.md`
- `templates/commands/map-scan.md`
- `templates/commands/plan.md`
- `templates/commands/quick.md`
- `templates/commands/research.md`
- `templates/commands/specify.md`
- `templates/commands/tasks.md`
- `templates/commands/taskstoissues.md`
- `templates/commands/test.md`
- `templates/commands/test-build.md`
- `templates/commands/test-scan.md`

Team-oriented command 模板保持独立：

- `templates/commands/implement-teams.md`
- `templates/commands/team.md`

## Task Orchestration Contract

强制 subagent 后，任务编排是核心质量门。

每个普通 `sp-*` command 在派发前必须完成任务拆分。每个 subagent 任务需要具备清晰任务契约：

- 任务目标
- 输入资料和权威上下文
- 允许读取范围
- 允许写入范围
- 禁止触碰范围
- 验收标准
- 验证命令或验证证据
- 结构化交付格式

主代理负责判断任务之间的关系：

- 哪些任务可以并行
- 哪些任务存在依赖
- 哪些共享文件或共享状态需要指定 owner
- 哪些交付需要按顺序合并
- 哪些结果需要二次 review 或验证

subagent 交付至少包含：

- 完成内容
- 改动文件或读取证据
- 验证结果
- 风险和未完成项
- 是否满足任务验收标准

主代理基于这些交付做整合、验证和状态更新。

## Generated Workflow Language

普通 `sp-*` 生成文案统一强调：

- 实质性任务必须由 subagent 执行
- 先编排，再派发
- 每个任务必须有明确 task packet 或等价 task contract
- subagent 必须提交结构化 handoff
- 主代理是 orchestrator

被动技能同步成为这个模型的共享解释层：

- `spec-kit-workflow-routing` 负责先路由到正确 `sp-*` workflow
- `subagent-driven-development` 负责说明主代理和 subagent 的协作契约
- `dispatching-parallel-agents` 负责多任务、多 lane 的并行编排要求

## Runtime and Model Vocabulary

orchestration 运行时和测试应表达同一个模型：

- 普通 `sp-*` 的 execution model 是 subagent mandatory
- 普通 `sp-*` 的 dispatch shape 表达单 subagent 或多 subagent 编排
- task packet / result handoff 是主代理和 subagent 的交界面
- team runtime vocabulary 只用于 team surface

## Documentation Updates

文档需要同步说明新的日常工作流语义：

- AGENTS.md 中的 Delegated Execution Defaults 和 managed rules
- README 中的 `sp-*` workflow guidance
- PROJECT-HANDBOOK.md 中的 high-value capabilities、hotspots、workflow routing
- `.specify/project-map/**` 中的 workflow、architecture、conventions 和 generated-surface docs

文档应把重点放在正向规则和编排质量上：`sp-*` 实质性任务使用 subagent，主代理负责组织和整合。

## Test Strategy

测试需要覆盖四层：

1. Template guidance tests：普通 `templates/commands/*.md` 都包含 subagent mandatory 规则和任务编排要求。
2. Passive skill tests：workflow routing、subagent-driven development、parallel dispatch 技能保持同一语义。
3. Integration tests：生成到各 agent 的命令/技能文案保留 mandatory subagent 规则。
4. Orchestration tests：policy/model 层输出符合普通 `sp-*` 的 subagent mandatory vocabulary，team surface 保持独立。

测试断言应聚焦：

- 普通 `sp-*` 生成面包含“必须使用 subagent”的正向规则
- 普通 `sp-*` 生成面要求先编排再派发
- 普通 `sp-*` 生成面要求 task packet 或等价 task contract
- 普通 `sp-*` 生成面要求结构化 handoff
- team surface 与普通 `sp-*` 语义分开

## Implementation Notes

实施时优先顺序：

1. 更新共享 vocabulary 和 orchestration policy/model。
2. 更新普通 command 模板。
3. 更新 passive skills。
4. 更新 integration 注入文案。
5. 更新 README、AGENTS、PROJECT-HANDBOOK 和 project-map。
6. 更新测试断言。
7. 运行 focused tests，再运行更宽的相关测试集。

每一步都应保持同一核心规则：所有 `sp-*` 相关工作流的实质性任务默认且必须使用 subagent 执行。
