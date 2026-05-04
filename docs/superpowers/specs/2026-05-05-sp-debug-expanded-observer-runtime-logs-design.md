# sp-debug 扩展观察者与运行时日志调查设计

Date: 2026-05-05
Status: Approved for implementation planning

## Goal

增强 `sp-debug` 的观察者阶段和运行时调查阶段，让调试在面对“用户只描述了表象、根因可能跨层、问题可能由间接因果导致”的场景时，能够更系统地扩宽候选面，并把日志调试正式纳入工作流。

这次设计解决的不是“再多写一些猜测”，而是三个更具体的问题：

- 观察者阶段虽然已经存在，但对跨层、间接因果、表象误导型问题的发散仍然不够宽。
- 运行时 bug 虽然已有“先看日志”的原则，但还没有把“何时必须先看日志、何时必须补日志、何时必须向用户索取日志”固化为明确流程门槛。
- agent 在排查运行时问题时，还没有稳定地产出“按项目类型分层的候选面 + 日志调查计划”，容易在没有足够证据时直接猜修。

## Problem Statement

当前 `sp-debug` 已经具备：

- `observer framing`
- `causal map`
- `investigation contract`
- `truth ownership`
- `transition memo`
- repeated failure 后更强的 instrumentation / research 提示

但围绕观察者和运行时日志调查，仍然存在五个断裂点：

1. 观察者阶段的候选扩散主要围绕已有 profile，仍然偏向少量候选和少量 family，不足以覆盖“前端看到的症状来自后端、缓存、队列、数据库、配置、部署或外部依赖”的间接致因。
2. 当前 observer stage 只有 `full` 和 `compressed` 两档，没有把“是否需要更强的多维观察”显式建模，也没有用户可确认的增强模式。
3. 运行时 bug 虽然已经强调 logs are first-class evidence，但并没有把“日志是否足够”升格成调查门槛；流程仍可能在日志不足时继续围绕假设自由前进。
4. agent 还没有稳定地产生“先看哪些日志、这些日志要区分哪些候选、如果日志不够应该补哪些点”的结构化调查计划。
5. 当 agent 不能自行访问运行日志时，流程没有要求它给用户产出高质量的日志索取包，容易退化成笼统地说“请提供日志”。

结果就是：

- 问题看起来在前端，但根因可能在后端 truth owner、缓存刷新、异步边界、环境配置或外部依赖，而 observer stage 未必能充分展开。
- 运行时 bug 的调查质量过度依赖操作者自觉，不是流程强约束。
- “日志不够”常常只停留在一句判断，没有进一步转化成 instrumentation 计划或用户协作请求。

## Locked Decisions

本次设计在进入文档前已经确认以下产品方向：

- 保留当前 `observer gate`，不允许彻底跳过观察者阶段。
- 新增的是“增强版观察者”，不是删除观察者。
- 增强版观察者不是全局参数；由 agent 在调试过程中根据问题特征主动建议开启，由用户确认。
- 增强版观察者只负责“多维展开 + 候选排序 + 日志调查计划”，不在 observer 阶段直接读取日志。
- 日志读取和日志分析发生在后续调查阶段。
- 对运行时 bug，要正式把日志调试纳入流程，强调现有日志优先、日志不足时主动补点、必要时明确向用户索要可操作的日志片段。
- 项目类型采用跨栈通用模型：`frontend/web-ui`、`backend/api-service`、`full-stack/web-app`、`worker/queue/cron`、`cli/automation`、`data-pipeline/integration`。
- 候选评估采用两层评分：先广覆盖轻量评分，再只对 Top 候选做工程化评分。

## Design Principles

- **薄观察者必过，厚观察者按需启用**：保留当前 root-cause discipline，同时给复杂运行时问题一个更强的发散层。
- **运行时问题先收集观测能力，再争论根因**：没有足够观测信号时，不允许自由猜修。
- **日志是证据，不是背景噪音**：现有 logs、stderr/stdout、test output、browser console、job output、DB logs、trace 都应被视为一等证据面。
- **观察者负责拉开候选面，调查阶段负责消费证据**：observer stage 不能直接变成调查阶段，也不能替代日志分析。
- **项目类型帮助限定范围，但不能绑死技术栈**：必须同时支持 Web、服务、worker、CLI、数据集成型项目。
- **高质量用户协作优于模糊索取**：当 agent 无法拿到运行日志时，必须给出时间窗口、目标文件、目标字段、期待信号，而不是一句“给我日志”。

## Options Considered

### Option A: 只改 think-subagent 提示词

只增强 `templates/worker-prompts/debug-thinker.md`，要求它多写一些候选、多想一些 family。

优点：

- 改动最小
- 不需要扩展 schema 和 graph

不足：

- 无法把“建议开启增强观察者”的行为固化到流程中
- 无法把日志计划、项目类型分流、评分模型、日志充分性门槛稳定写入状态
- 最终容易变成提示词风格优化，而不是 debug contract 增强

### Option B: 观察者阶段彻底可跳过

允许用户显式跳过 observer stage，直接进入 repro / logs / code。

优点：

- 看起来更快

不足：

- 直接削弱了当前 `sp-debug` 的根因纪律
- 与当前 `observer_framing_completed`、`transition_memo`、`causal_map`、`investigation_contract` 的结构性前置条件冲突
- 无法满足“问题可能是间接因果，用户描述未必可靠”的设计目标

### Option C: 薄观察者必过 + 增强观察者可选

保留当前 observer gate，把更强的多维观察和日志调查计划做成用户确认的增强层，并在运行时 bug 下由 agent 主动建议启用。

这是本次选定方案。

原因：

- 保留现有 `sp-debug` 的结构性约束
- 精确命中“复杂运行时问题需要更宽候选面”的真实需求
- 可以把运行时日志调查作为后续阶段硬约束，而不是把 observer stage 变成日志读取器

## Selected Model

`sp-debug` 的主流程保持：

`observer framing -> investigation contract -> evidence investigation -> fixing -> verifying`

但新增一个用户确认的增强层：

`standard observer -> optional expanded observer -> investigation contract -> runtime evidence/log investigation`

其中：

- `standard observer` 继续是必经阶段
- `expanded observer` 只在需要时建议开启
- `expanded observer` 的输出成为 `investigation contract` 和后续日志调查的强化输入
- 对运行时 bug，`investigating` 阶段新增日志充分性门槛

## Activation Policy

### 何时建议开启 `expanded observer`

当满足以下任一条件时，agent 应主动建议用户开启增强观察者：

- 问题属于运行时 bug，而不是纯编译错误或纯静态错误
- 用户描述主要是“现象”，不是精确错误位置
- 影响面疑似跨前端 / 后端 / 数据库 / 缓存 / 队列 / 外部依赖 / 环境部署边界
- 当前日志或错误输出不足以直接收敛到单一候选
- 连续两轮候选/实验后仍然没有收敛

### 用户交互模型

建议文案要明确说明：

- 为什么当前问题符合增强观察者的触发条件
- 启用后会额外产出什么
- 启用后不会直接读日志，而是生成多维候选与日志调查计划

用户可：

- 同意开启
- 拒绝开启

拒绝开启不会阻断标准 `sp-debug`，但系统仍应记录这是一次“推荐但未启用”的增强观察者机会。

## State Model Changes

建议在 `DebugGraphState` 上新增以下状态。

### Expansion State

- `observer_expansion_status`
  - `not_applicable`
  - `suggested`
  - `user_declined`
  - `enabled`
  - `completed`
- `observer_expansion_reason`
  - 说明为什么建议启用，例如 `runtime_cross_layer_symptom`、`logs_insufficient`、`hypothesis_not_converging`
- `project_runtime_profile`
  - `frontend/web-ui`
  - `backend/api-service`
  - `full-stack/web-app`
  - `worker/queue/cron`
  - `cli/automation`
  - `data-pipeline/integration`
- `symptom_shape`
  - `exact_error`
  - `phenomenon_only`
- `log_readiness`
  - `unknown`
  - `sufficient_existing_logs`
  - `insufficient_need_instrumentation`
  - `user_must_provide_logs`

### Expanded Observer Payload

新增一个聚合结构，例如 `ExpandedObserverState`，建议至少包含：

- `dimension_scan`
- `candidate_board`
- `top_candidates`
- `log_investigation_plan`

#### `dimension_scan`

按固定维度记录观察结果：

- `symptom_layer`
- `caller_or_input_layer`
- `truth_owner_or_business_layer`
- `storage_or_state_layer`
- `cache_queue_async_layer`
- `config_env_deploy_layer`
- `external_boundary_layer`
- `observability_layer`

#### `candidate_board`

每个候选建议包含：

- `candidate_id`
- `dimension_origin`
- `family`
- `candidate`
- `why_it_fits`
- `indirect_path`
- `surface_vs_truth_owner_note`
- `light_scores`

#### `top_candidates`

从 `candidate_board` 中选出的 Top 3 候选，附加第二层评分：

- `engineering_scores`
- `investigation_priority`
- `recommended_log_probe`

#### `log_investigation_plan`

建议字段：

- `existing_log_targets`
- `candidate_signal_map`
- `log_sufficiency_judgment`
- `missing_observability`
- `instrumentation_targets`
- `instrumentation_style`
- `user_request_packet`

## Scoring Model

本次采用两层评分模型。

### 第一层：轻量评分

用于所有候选，目标是“先把可能性铺开”。

评分维度：

- `likelihood`
- `impact_radius`
- `falsifiability`
- `log_observability`

### 第二层：工程化评分

只对 Top 3 候选执行，目标是决定“先查谁、先看什么日志、先补什么点”。

评分维度：

- `cross_layer_span`
- `indirect_causality_risk`
- `evidence_gap`
- `investigation_cost`

### 使用原则

- 分数用于排序调查优先级，不用于宣布真因。
- 第一层强调广覆盖，第二层强调证据投资回报。
- 不能因为一个候选得分最高，就跳过对关键 contrarian candidate 的最小消解。

## Expanded Observer Responsibilities

增强观察者只负责以下内容：

- 按项目类型和固定维度扩展候选面
- 明确哪些候选更像表象层，哪些更像 truth owner 或边界断裂
- 产出两层评分与优先调查顺序
- 产出日志调查计划

增强观察者明确不负责：

- 读取现有日志
- 运行 repro
- 查看源码或测试
- 直接确认根因

这保证 observer stage 仍然是“高质量 framing”，而不是提前侵入调查阶段。

## Runtime Investigation Protocol

对运行时 bug，`investigating` 阶段新增明确的日志协议。

### Step 1: 先评估现有日志面

进入运行时调查后，必须先记录：

- 要先看哪些现有日志
- 每类日志打算区分哪些候选
- 当前日志是否足以收敛

可消费的证据面包括：

- application logs
- stderr / stdout
- targeted test output
- browser console
- worker / job logs
- database / query logs
- trace / spans
- external service error payloads

### Step 2: 判断日志是否充分

如果现有日志已经足够缩小候选面，继续证据调查。

如果现有日志不足，则必须显式进入以下动作之一：

- 添加或调整 instrumentation
- 重跑 repro 收集新日志
- 向用户索取明确的日志包

### Step 3: 日志不足时禁止空猜修复

当问题属于运行时 bug，且日志或现有证据仍不足以区分高优先候选时：

- 不允许直接进入 `fixing`
- 不允许继续无证据地切换多个局部假设
- 必须先提升观测能力

换句话说，运行时 bug 的最小修复门槛不只是“有一个 plausible hypothesis”，还要有足够的观测信号支撑它比其他候选更强。

## Instrumentation Policy

当日志不足时，agent 应优先设计可保留、结构清晰的 instrumentation，而不是撒网式打印。

### 优先补点位置

- 输入边界
- 关键决策分支
- truth owner 更新点
- control state -> observation state handoff
- 缓存 / 队列 / 异步边界
- 外部调用前后

### 风格要求

- 默认优先结构化日志或 trace
- 临时诊断日志允许存在，但必须有明确的证据目标
- 避免“到处 print / log”的低信噪比补点

## User Log Request Packet

如果 agent 无法自行访问运行日志，必须生成高质量的用户协作请求，而不是笼统索取。

`user_request_packet` 建议至少包含：

- `target_source`
  - 要求用户提供哪个日志文件、哪个命令输出、哪个控制台片段
- `time_window`
  - 需要的时间窗口或重现窗口
- `keywords_or_fields`
  - 重点关注哪些字段、request id、job id、状态转换、错误码
- `why_this_matters`
  - 这段日志能区分哪些候选
- `expected_signal_examples`
  - 看到了什么会支持候选 A，没看到什么会打掉候选 B

这样用户就不需要猜 agent 想看什么，agent 也不会把下一步建立在含糊的“等日志”上。

## Project Runtime Profiles

增强观察者应先把项目问题归入一个运行时轮廓，再做维度扫描。

### `frontend/web-ui`

重点观察：

- browser-side symptom
- API contract or publish boundary
- render / state sync timing
- console output and network error surface

### `backend/api-service`

重点观察：

- request boundary
- business truth owner
- persistence / cache boundary
- structured application logs

### `full-stack/web-app`

重点观察：

- 前端症状与后端 truth owner 是否脱钩
- cache / async / projection 是否制造间接因果
- browser、server、DB 三层日志的串联

### `worker/queue/cron`

重点观察：

- enqueue / dequeue / retry / ack 边界
- queue truth owner
- delayed consistency or stale ownership
- job logs / scheduler logs / queue metrics

### `cli/automation`

重点观察：

- command input/output boundary
- environment / config / file system side effects
- subprocess logs and stderr

### `data-pipeline/integration`

重点观察：

- source -> transform -> sink 的闭环
- schema / contract drift
- batch timing / partial failure / replay
- connector logs and row-level error signals

## Graph and Template Changes

### `templates/commands/debug.md`

需要新增：

- 何时建议开启增强观察者
- 用户确认后的行为
- 运行时 bug 的日志协议
- 日志不足时的 fix gate 阻塞规则
- 用户日志索取包的要求

### `templates/worker-prompts/debug-thinker.md`

需要升级为：

- 多维扫描
- 两层评分
- 项目类型分流
- 日志调查计划生成

同时继续保持“不读日志、不读源码、不跑命令”的 observer hard constraints。

### `templates/worker-prompts/debug-contract-planner.md`

需要让 Stage 1B 显式消费：

- 增强观察者的候选排序
- 日志调查计划
- 哪些候选更像表象层

### `src/specify_cli/debug/schema.py`

需要新增增强观察者、项目轮廓、日志充分性、日志计划等字段。

### `src/specify_cli/debug/graph.py`

需要新增：

- 运行时 bug 识别
- 建议开启增强观察者的触发逻辑
- 用户确认点
- 调查阶段的日志门槛
- 日志不足时阻止进入 fixing 的 gate

### `src/specify_cli/debug/persistence.py`

需要持久化新增状态，并在 handoff / research checkpoint / human review report 中展示：

- 是否建议过增强观察者
- 用户是否开启
- 项目运行时轮廓
- 当前日志充分性判断
- 日志调查计划摘要

### `src/specify_cli/debug/cli.py`

需要在 checkpoint 输出中展示：

- 扩展观察者状态
- Top 候选
- 先看哪些日志
- 是否需要补 instrumentation

## Verification Strategy

实现后建议至少覆盖以下测试面。

### Template / Contract Tests

- `templates/commands/debug.md` 包含增强观察者触发与日志协议
- `templates/worker-prompts/debug-thinker.md` 包含两层评分和日志计划合同

### Persistence Tests

- 新字段 round-trip
- handoff report 展示增强观察者和日志计划摘要
- user log request packet 能持久化

### Graph Tests

- 运行时 bug 且症状型描述时，会建议开启增强观察者
- 用户拒绝后仍能继续标准 observer
- 增强观察者完成后，状态正确推进
- 运行时 bug 在 `log_readiness` 不足时不能直接进入 fixing
- 不能访问日志时会生成高质量 `user_request_packet`

### CLI / Checkpoint Tests

- checkpoint 输出显示扩展观察者状态和日志计划
- human handoff 报告能说明当前是否卡在日志不足 / 需要用户提供日志

## Non-Goals

本次设计明确不做以下事情：

- 不把 observer stage 改成日志分析器
- 不强制每次 debug 都询问是否开启增强观察者
- 不把 `sp-debug` 变成 Web 专用工作流
- 不引入一个全新独立的 `sp-runtime-debug` workflow

## Acceptance Criteria

当本次设计实现后，应满足以下用户可见效果：

- 遇到复杂运行时 bug 时，agent 会主动建议用户开启更强的观察者模式，而不是马上盯住一个点。
- 增强观察者会从多个维度大胆展开问题，不局限于用户表面描述。
- observer stage 会产出结构化的日志调查计划，但不会越权直接读日志。
- 调查阶段会先消费现有日志；日志不足时会主动补 instrumentation 或向用户索取明确日志包。
- 在运行时 bug 上，如果没有足够日志证据，流程不会允许 agent 直接猜修。

## Implementation Direction

建议按以下顺序落地：

1. 扩展 `schema.py` 和 `persistence.py`
2. 升级 `debug-thinker` 与 `debug-contract-planner` 提示词
3. 在 `graph.py` 中接入增强观察者触发、确认与日志 gate
4. 更新 `debug.md` 和 CLI 展示
5. 补全 persistence / graph / template tests

## Summary

这次设计的核心不是“让 observer 再多写几条原因”，而是把 `sp-debug` 升级成：

- 薄观察者必过
- 厚观察者按需开启
- 运行时问题以日志证据为第一调查面
- 日志不足时先提升观测能力，再允许修复

这样 `sp-debug` 才能更稳定地处理“用户看到的是表象、根因却藏在别处”的问题，同时避免在运行时 bug 上继续靠猜测推进。
