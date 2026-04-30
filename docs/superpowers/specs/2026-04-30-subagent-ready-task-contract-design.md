# 子代理就绪任务契约设计

**日期：** 2026-04-30
**状态：** 待审批
**前序设计：**
- [2026-04-30-subagents-first-workflow-design.md](./2026-04-30-subagents-first-workflow-design.md)
- [2026-04-30-sp-subagent-mandatory-design.md](./2026-04-30-sp-subagent-mandatory-design.md)
- [2026-04-23-multi-agent-task-shaping-design.md](./2026-04-23-multi-agent-task-shaping-design.md)

## 目标

让 `sp-tasks` 产出的每一个 task 成为 **自包含的施工指令** —— worker（子代理）拿到 task 后不需要回头问 leader 任何问题、不需要自己探索代码风格、不需要猜测验收标准，读一遍就直接开干。

## 问题陈述

当前 `sp-plan` → `sp-tasks` → `sp-implement` 链路中存在三个断层：

1. **任务边界模糊**：tasks.md 按逻辑步骤拆分，但未验证每个 task 是否真的可由一个子代理独立完成。worker 拿到任务后发现自己缺上下文、缺文件、或者任务太大超出单次会话预算。

2. **缺少读写范围声明**：leader 做并行分发时只能靠人工判断"这俩任务会不会改同一个文件"。没有显式的 `write_scope` / `read_scope` / `forbidden` 声明，并行分发有风险。

3. **契约散落在长文中**：plan.md、data-model.md、contracts/*.md 各几十到几百行。worker 需要自己翻几百行文档找"我这个 task 到底需要什么信息"，效率低且容易遗漏。

## 范围

- `templates/command-partials/tasks/shell.md`：核心改动面，升级任务输出格式
- `templates/command-partials/plan/shell.md`：微调，增加章节锚定要求
- `templates/commands/implement.md`：增加预分发校验层和升级策略
- `src/specify_cli/execution/packet_schema.py`：可能需要新增可选字段
- `src/specify_cli/orchestration/delegation.py`：增加 task contract 就绪检查
- 测试层：template guidance tests + contract tests + integration tests

## 设计

### 1. 升级后的 tasks.md Task 格式

每个 task 必须包含以下全部字段。字段按"身份 → 依赖 → 上下文导航 → 范围边界 → 产出与验收 → 交付与恢复"的逻辑分组：

```markdown
## T{n}: {一句话描述}

### 身份
| 字段 | 值 |
|------|-----|
| agent | {从 agent-teams 角色池指派} |
| depends_on | [T{x}: {简述}, T{y}: {简述}] |
| parallel_safe | true | false |

### 上下文导航
| 需要什么 | 去哪里找 |
|----------|---------|
| {具体知识点} | {文件名}#{章节/锚点} |
| {参考实现} | {文件路径}（{简述相似之处}） |

### 范围边界
| 字段 | 值 |
|------|-----|
| write_scope | [src/path/file.ts, tests/path/file.test.ts] |
| read_scope | [src/other/, docs/spec.md] |
| forbidden | [src/secrets/, .env, src/config/] |

### 预期产出
- src/path/file.ts（新建/修改）
- tests/path/file.test.ts（新建，≥80% 覆盖率）

### 禁止行为
- {具体的行为约束，如：不引入新依赖、不修改公开接口}

### 验收条件
- [ ] {可客观验证的条件}

### 验证命令
```
{可直接运行的 shell 命令}
```

### 交付格式
- status: success | failed | blocked
- changed_files: [...]
- validation_output: {...}
- concerns: [...]
- recovery_hints: [...]

### 失败处理
| 字段 | 值 |
|------|-----|
| retry_max | 2 |
| escalation | {角色名}（{何时触发}） |
```

### 2. 各字段的设计理由

**agent（agent 指派）**

从 agent-teams 已有角色池中指派。每个 task 在被创建时就确定了"谁来做"，`sp-implement` 不再需要临时推断。

角色池（与 `extensions/agent-teams/engine/prompts/` 对齐）：

| 角色 | 适用场景 |
|------|---------|
| security-reviewer | 认证、授权、加密、输入验证 |
| test-engineer | 测试编写、测试修复 |
| style-reviewer | UI 组件、样式、布局 |
| performance-reviewer | 性能优化、查询调优 |
| quality-reviewer | 代码质量、重构 |
| api-reviewer | API 设计、契约实现 |
| debugger | 诊断、问题定位 |
| code-simplifier | 代码简化、去重 |
| build-fixer | 构建修复、依赖问题 |
| git-master | 分支管理、合并操作 |

当无特定角色匹配时，使用通用 `executor` 角色。

**parallel_safe（并行安全标记）**

由 `sp-tasks` 计算。两个 task 可以并行当且仅当：
- 它们的 `write_scope` 无交集
- 它们的 `write_scope` 不与对方的 `read_scope` 有交集（严格模式）

`sp-implement` 的 leader 从 `depends_on` 自动推导并行批次，`parallel_safe` 作为辅助信号。如果两个 task 无依赖但 `parallel_safe: false`，说明存在未建模的共享状态冲突，leader 应串行执行。

**上下文导航（不冗余原则）**

不复制内容，只写精确的文件路径 + 章节/锚点。worker 按指针去找。这要求 `sp-plan` 产出的文档使用可锚定的章节标题（见第 3 节）。

**范围边界（三区模型）**

- `write_scope`：task 产出的文件列表（精确到文件）
- `read_scope`：只读依赖（可以是目录）
- `forbidden`：绝对禁止触碰（安全边界）

leader 在并行分发前做隔离检查：两个 task 的 `write_scope` 有交集 → 不能并行。

**验证命令（可执行验证）**

验收条件写成自然语言需要 worker 自己翻译成命令。直接给可运行命令，worker 执行完就知道自己过没过。

**失败处理（升级策略）**

默认策略（可被 task 级别覆盖）：
1. 首次失败 → 同 agent 重试 1 次
2. 再次失败 → 升级到 `escalation` 指定的角色（默认 debugger）
3. 升级后仍失败 → 标记 `blocked`，携带 `recovery_hints`

### 3. sp-plan 的微调

`sp-plan` 的产出逻辑不变。在输出 contract 中增加一条要求：

> 所有产出的 markdown 文档（plan.md、data-model.md、contracts/*.md）必须使用可锚定的标题（`## Section Name`），确保 `sp-tasks` 阶段能生成精确的 `文件名#章节名` 导航指针。

在 `templates/command-partials/plan/shell.md` 的 Guardrails 中追加：

```markdown
- Use anchorable section headings (## Section Name) in all output artifacts so that downstream task generation can produce precise file#section context pointers.
```

### 4. sp-implement 的预分发校验层

`sp-implement` 首次读取 tasks.md 后，在分发前对每个 task 执行校验：

```text
PRE-DISPATCH VALIDATION（每个 task）:

1. agent_exists
   → task.agent 在角色池中存在？
   → 不存在 → 自动修正为最接近的角色或 executor

2. scope_paths_exist
   → write_scope / read_scope 中每个路径在仓库中实际存在？
   → 不存在 → 标记 warning，不阻塞分发但提醒 leader 注意

3. deps_acyclic
   → depends_on 不能形成循环依赖
   → 存在循环 → 阻塞分发，要求 leader 修正 tasks.md

4. context_nav_valid
   → 上下文导航中每个指针指向的章节/锚点在目标文件中存在？
   → 不存在 → 标记 warning

5. forbidden_safe
   → forbidden 路径是否包含 .env、credentials、secrets 等敏感模式？
   → 未包含 → 自动追加默认 forbidden 模式
```

校验不通过的处理：
- Error 级别（循环依赖、agent 不存在）→ 就地修正，修正失败则阻塞
- Warning 级别（路径不存在、锚点缺失）→ 记录但继续分发，worker 自行处理

### 5. 完整示例

```markdown
## T3: 实现 JWT 认证中间件

### 身份
| 字段 | 值 |
|------|-----|
| agent | security-reviewer |
| depends_on | [T1: AuthService 接口定义, T2: JWT 工具函数] |
| parallel_safe | true |

### 上下文导航
| 需要什么 | 去哪里找 |
|----------|---------|
| JWT payload 结构 | data-model.md#AuthPayload |
| token 过期策略 | plan.md#token-expiry-strategy |
| 受保护路由列表 | contracts/auth-api.md |
| 错误响应标准格式 | contracts/error-response.md |
| 参考实现 | src/middleware/ratelimit.ts（相同的中间件模式） |

### 范围边界
| 字段 | 值 |
|------|-----|
| write_scope | [src/middleware/auth.ts, tests/auth/middleware.test.ts] |
| read_scope | [src/auth/types.ts, contracts/auth-api.md, contracts/error-response.md] |
| forbidden | [src/db/, .env, src/config/] |

### 预期产出
- src/middleware/auth.ts（新建）
- tests/auth/middleware.test.ts（新建，≥80% 覆盖率）

### 禁止行为
- 不引入新的 npm 依赖
- 不直接访问数据库（通过 AuthService 接口）
- 不修改 src/auth/types.ts 中的已有公开类型

### 验收条件
- [ ] 有效 token → 注入 AuthPayload 到 req.context，继续请求链
- [ ] 过期 token → 返回 401 + 标准错误响应格式
- [ ] 无 Authorization header → 返回 401
- [ ] 畸形 token → 返回 400
- [ ] 白名单路径正常放行
- [ ] 安全 lint 无告警

### 验证命令
```
npx jest tests/auth/middleware.test.ts --coverage
npx eslint src/middleware/auth.ts
npx tsc --noEmit
```

### 交付格式
- status: success | failed | blocked
- changed_files: ["src/middleware/auth.ts", "tests/auth/middleware.test.ts"]
- validation_output: {"jest": "PASS", "eslint": "clean", "tsc": "clean"}
- concerns: [] | ["具体关注项"]
- recovery_hints: [] | ["建议的恢复方向"]

### 失败处理
| 字段 | 值 |
|------|-----|
| retry_max | 2 |
| escalation | debugger（retry 耗尽后升级诊断） |
```

## 字段必要性说明

| 字段 | 缺了会导致什么问题 |
|------|-------------------|
| agent | leader 需要临时推断角色，可能选错 |
| depends_on | worker 不知道该等谁，可能读未完成的工作 |
| parallel_safe | leader 可能把冲突的 task 并行分发 |
| 上下文导航 | worker 花大量 token 自己探索，或遗漏关键约束 |
| write_scope | worker 可能写了不该写的文件 |
| read_scope | worker 不知道自己去哪里找信息 |
| forbidden | worker 可能误改敏感文件 |
| 预期产出 | worker 不确定应该交付什么 |
| 禁止行为 | worker 可能引入新依赖、改公开接口等 |
| 验证命令 | worker 用主观判断代替客观验证 |
| 交付格式 | handoff 不结构化，leader 整合困难 |
| 失败处理 | 失败后无恢复方向，leader 需要重新分析 |

## 实施步骤

1. **升级 tasks shell.md**：将新的 task 格式写进 `templates/command-partials/tasks/shell.md` 的 Output Contract
2. **微调 plan shell.md**：在 Guardrails 中追加锚定标题要求
3. **升级 implement.md**：增加 Pre-Dispatch Validation 章节
4. **更新 packet_schema.py**：`WorkerTaskPacket` 增加可选字段（agent、write_scope、read_scope、forbidden、context_nav、verify_commands、escalation）
5. **升级 delegation.py**：增加 `validate_task_contract()` 函数
6. **更新 AGENTS.md / PROJECT-HANDBOOK.md**：文档同步
7. **测试**：
   - `pytest tests/test_specify_guidance_docs.py` —— tasks 模板产出符合新格式
   - `pytest tests/codex_team/test_codex_guidance_routing.py` —— agent 角色在池中存在
   - `pytest tests/contract/test_codex_team_generated_assets.py` —— packet schema 兼容
   - `pytest tests/orchestration/` —— 校验逻辑覆盖

## 非目标

- 不改变 `sp-plan` 的核心逻辑（它仍然是设计阶段）
- 不改变 `sp-implement` 的 leader/worker 模型
- 不要求 `sp-tasks` 在生成时保证 100% 准确的 field 值（校验层会兜底）
- batch_id 不从 `sp-tasks` 显式生成，由 `sp-implement` 从 depends_on 推导

## 验收标准

- `sp-tasks` 产出的每个 task 包含：agent、depends_on、上下文导航表、write_scope / read_scope / forbidden、预期产出、验证命令、交付格式、失败处理
- `sp-plan` 的 Guardrails 包含锚定标题要求
- `sp-implement` 的 leader 在分发前执行预分发校验
- 上下文导航不重复内容，只写精确指针
- worker 拿到 task 后不需要额外探索或询问即可开始执行
