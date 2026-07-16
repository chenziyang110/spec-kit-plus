# Universal Semantic Work Contract v1

A unified natural-language routing contract for project-cognition-backed agent work.

Execution handoff: see `docs/design/universal-semantic-work-contract-handoff.md`
for the release gate and next-version checklist.

## Executive Summary

`Universal Semantic Work Contract v1` 解决的是自然语言需求到项目事实之间缺少稳定协议的问题。

用户表达是活的：同一个意思可能有很多说法，而且常常是中文、英文、项目术语混合。`project-cognition` 的数据库是静态的：它保存项目事实、别名、路径、图关系和历史观察，但不应该被要求直接理解所有口语表达。

最佳设计不是让数据库变成万能自然语言理解器，也不是让 Agent 自由猜文件，而是：

```text
User request
-> Agent extracts Need + Facets
-> project-cognition semantic-intake returns Candidate Universe
-> Agent builds RouteContract + OwnerBundle
-> Coverage and PermissionDecision gate action
-> Verification gates final claims
-> LearningCandidate records reusable evidence
```

v1 的目标是 **Semantic Routing**，不是全自动修复。第一版只承诺让系统更准地理解“用户这句话在项目里可能落到哪里”，并明确：

```text
哪些候选被选中
哪些近似概念只是对照
哪些误匹配被排除
还缺什么证据
当前最多允许做到什么
```

核心不变量：

```text
Agent inference is not project fact.
project-cognition provides the candidate universe, not the final action decision.
PermissionDecision gates every action and final claim.
semantic-intake does not authorize code changes.
Workflow names are intent hints, not separate routing systems.
Learning must be conservative, conditional, and reversible.
```

## Why This Exists

这个能力存在的原因不是某一次 H5 环境变量页面没匹配准，而是当前系统缺少一层稳定协议：

```text
用户自然语言 -> 项目真实语义 -> 可行动边界
```

当前三方能力没有明确分工：

| 角色 | 当前容易出的问题 |
| --- | --- |
| 用户 | 表达口语化、多义、上下文省略 |
| Agent | 能理解大意，但可能跳过项目事实直接猜 |
| project-cognition | 有项目事实，但不能天然理解所有说法 |

典型错配：

```text
“环境变量页面” -> .env 配置
“H5 环境不对” -> workflow runtime environment
“客户端正常 H5 不正常” -> 泛泛搜索 client/env
“帮我看看正常吗” -> 被当成要直接修
```

这些错配的根因不是搜索算法单点不够强，而是没有一个中间合同要求系统必须说明：

```text
我把用户话理解成什么
这个理解命中了哪些项目概念
哪些近似概念被排除
证据够不够
当前能不能改
最终能不能说完成
```

## Risks If We Do Nothing

如果不做统一语义工作合同，系统会继续依赖关键词匹配、workflow intent、Agent 自己猜、零散 prompt 规则和局部学习。长期风险包括：

| Risk | Impact |
| --- | --- |
| Same meaning, different words, different results | 用户同一个意思换种说法，系统可能落到不同 owner |
| Workflow fragmentation | `sp-debug` 准了，`sp-implement` / `sp-plan` / `sp-review` 仍然跑偏 |
| Agent overconfidence | Agent 越会理解人话，越可能自信地猜错 owner 或跳过验证 |
| Learning pollution | 一次错误 alias 会反复影响后续任务 |
| Release/runtime drift | prompt 要求新能力，但下游 runtime 或 launcher 过旧 |
| No debuggability | 失败只能归因成“Agent 没理解”，无法定位到 facet/candidate/surface/permission/learning |
| Unsafe autonomy | 先自动执行，再事后找理由 |

最大风险不是“匹配偶尔不准”，而是：

```text
系统越自动，错误越隐蔽，影响越长期。
```

## Target Need

建立一个统一自然语言入口，让 Agent 作为语义中介，把用户表达转换成项目事实可约束的 `WorkContract`，再由 `project-cognition` 返回候选语义空间，由 permission gating 决定能答、能查、能改、能声明到什么程度。

用户侧目标：

- 用户可以用口语表达需求、bug、问题、改动意图。
- 用户不需要选择 `debug / implement / plan / review`。
- 系统能把表达稳定映射到项目内真实概念、owner、验证路径。
- 系统不会因为理解了大概意思就越权修改或过度声明。

系统侧目标：

- 所有任务先形成 `WorkContract`。
- 所有候选来自 `project-cognition` 的项目事实。
- 所有行动由 `PermissionDecision` 控制。
- 所有学习写入必须带证据等级和可撤销路径。

## What v1 Delivers

v1 交付 **Semantic Routing**：

```text
统一自然语言 intake
Agent facet extraction
project-cognition semantic-intake
candidate universe
selected / contrast / rejected concepts
RouteContract
OwnerBundle 草案
PermissionDecision
LearningCandidate M1
shared prompt partial
golden eval baseline
cross-CLI consistency anchors
runtime fallback/stale diagnostics
```

v1 的输出不是“直接修好了”，而是类似：

```yaml
normalized_need: H5/web environment settings page access exception
primary_candidate: environment-settings-page
contrast_candidates:
  - env-config
rejected_candidates:
  - workflow-environment
missing_evidence:
  - exact exception source
  - verification path
permission: P2
allowed:
  - targeted inspect
blocked:
  - code change
  - root cause claim
  - fixed claim
```

## What v1 Does Not Deliver

v1 明确不交付：

```text
自动修复所有 bug
自动实现所有需求
自动 canonical learning
自动 release-safe 判断
自动跨模块大重构
让 project-cognition 独立理解所有自然语言
```

如果 v1 做完后系统只是更会“改代码”，但没有更会“判断证据够不够”，那就是做偏了。

## Design Principles

### 1. Agent Inference Is Not Project Fact

Agent 可以理解用户意图、抽取 facets、比较候选，但 Agent 的推断不能直接变成项目事实。

项目事实只能来自：

```text
project-cognition indexed graph
live source evidence
runtime/test evidence
explicit user confirmation
```

### 2. project-cognition Provides Candidate Universe, Not Final Action

`semantic-intake` 的职责是返回候选语义空间：

```text
primary candidates
contrast candidates
rejected candidates
owner hints
missing evidence
permission hint
learning candidate
```

它不授权修改，不读 live source，不声称根因。

### 3. Low Evidence Means Low Permission

权限必须随证据升级：

```text
只有词表命中 -> 只能解释候选
有候选 owner -> 可以 targeted inspect
有 coverage + verification -> 可以 scoped change
有验证结果 -> 可以 final claim
```

用户说“直接改”或 Agent 很确定，都不能跳过证据。

### 4. Surface Type Beats Text Similarity

很多误匹配来自文本相似：

```text
环境变量页面
环境变量配置
运行环境
workflow environment
```

这些文本相似，但 surface 不同。v1 必须优先判断：

```text
用户动作 + surface type + behavior + context
```

### 5. Selected, Contrast, and Rejected Are All Required

只返回 winner 不够。系统必须保留：

```text
selected: 当前主候选
contrast: 近似但不确定/非主路径
rejected: 明确误匹配
```

### 6. Verification Is Part Of Routing

验证不是改完代码之后才想。形成 owner bundle 时就要寻找：

```text
positive verification
regression verification
risk surfaces
```

没有 verification owner，不能进入 `change_ready`。

### 7. Final Claims Must Match Evidence

允许说什么取决于 evidence level：

```text
没有 truth owner -> 不能说已定位
没有 positive + regression verification -> 不能说已修复
没有 success signals 全满足 -> 不能说已完成
没有 release-level checks -> 不能说 release-safe
```

### 8. Learning Is Conservative, Conditional, And Reversible

学习不能把一次猜测写成事实。v1 默认只生成 `M1 candidate`。ambiguous phrase 必须用 conditional alias。

### 9. Workflow Names Are Intent Hints

`sp-debug`、`sp-implement`、`sp-plan`、`sp-review` 不能是四套路由系统。它们只能提供 bias：

```text
debug -> inspect-biased
implement -> change-requested
plan -> planning output
review -> risk-focused
```

### 10. Cross-CLI Semantics Must Stay Consistent

Codex、Claude、Gemini、Cursor、Kimi、Trae、Antigravity 等可以有不同格式和工具调用方式，但不能有不同语义规则。

Review 标准：

```text
A change is valid only if it improves semantic precision, evidence quality, or permission safety without weakening the shared WorkContract.
```

## Glossary

| Term | Meaning |
| --- | --- |
| `WorkContract` | 统一入口的内部工作合同 |
| `NeedContract` | 用户真正想要什么 |
| `FacetSet` | goal / surface / behavior / context / constraint |
| `Candidate Universe` | project-cognition 返回的候选语义空间 |
| `Selected Concept` | 当前主候选 |
| `Contrast Concept` | 相似但非主路径候选 |
| `Rejected Concept` | 明确误匹配 |
| `OwnerBundle` | primary / supporting / truth / verification / excluded owner 集合 |
| `RouteLevel` | 知道多少：`R0` 到 `R5` |
| `PermissionState` | 能做什么：`P0` 到 `P4` |
| `EvidenceRank` | 证据来源强度：`E0` 到 `E4` |
| `VerificationLevel` | 验证强度：`V0` 到 `V4` |
| `MemoryLevel` | 学习可信度：`M0` 到 `M4` |
| `semantic-intake` | project-cognition 的 v1 语义候选接口 |
| `FinalClaimGate` | 控制 explain / located / fixed / completed / release_safe 等最终说法 |

一句话区分：

```text
Facet 是用户请求的结构。
Candidate 是项目事实里的可能落点。
Route 是当前选择和排除理由。
Owner 是要查/改/验证的实际对象。
Permission 是现在允许做什么。
Evidence 是为什么允许。
Learning 是以后能不能复用。
```

## Architecture

系统由四个主要层组成：

```text
User / Agent Layer
Project Cognition Layer
Runtime Permission Layer
Learning Layer
```

标准链路：

```text
1. User Request
2. Agent NeedContract
3. Agent Facets
4. project-cognition semantic-intake
5. Candidate Universe
6. Agent RouteContract
7. OwnerBundle
8. CoverageContract
9. PermissionDecision
10. Allowed Action
11. Live Evidence / Verification
12. Final Claim Gate
13. LearningCandidate
```

组件边界：

| 能力 | Agent | project-cognition | Permission | Learning |
| --- | --- | --- | --- | --- |
| 理解用户口语 | yes | no | no | no |
| 抽 facets | yes | validate/score | no | no |
| 查项目事实 | no | yes | no | no |
| 返回候选宇宙 | no | yes | no | no |
| 选择 route | yes | hints | validate | no |
| 授权修改 | no | no | yes | no |
| 验证 final claim | no | hints | yes | no |
| 写 confirmed memory | no | evidence source | gated | yes |

关键边界：

```text
semantic-intake output can raise the system to P2, but never to P3 by itself.
P3 requires live evidence, owner coverage, and verification owner.
P4 requires verification results and final claim alignment.
```

## WorkContract v1

`WorkContract` 是统一入口的内部工作合同。任何项目请求，无论来自旧 `sp-debug`、`sp-implement`、普通自然语言，还是后续统一入口，都必须先形成这个合同。

```yaml
work_contract:
  version: 1
  raw_request: string
  conversation_context:
    project_role: upstream | downstream | unknown
    prior_intent: string | null
    active_contract_id: string | null

  need:
    interpreted_goal: string
    expected_outcome: string
    mutation_intent: none | inspect | change | unknown
    task_shape:
      - explanation
      - investigation
      - scoped_change
      - broad_change
      - verification
      - documentation
      - planning
    success_signals:
      - string
    blocking_ambiguities:
      - string

  facets:
    goal:
      required: []
      supporting: []
      optional: []
    surface:
      required: []
      supporting: []
      optional: []
    behavior:
      required: []
      supporting: []
      optional: []
    context:
      required: []
      supporting: []
      optional: []
    constraint:
      required: []
      supporting: []
      optional: []

  route:
    normalized_need: string
    selected_concepts:
      - id: string
        surface_type: string
        confidence: low | medium | high
        evidence_rank: E0 | E1 | E2 | E3 | E4
        basis:
          - string
    contrast_concepts:
      - id: string
        surface_type: string
        reason: string
    rejected_concepts:
      - id: string
        surface_type: string
        false_match_type: string
        reason: string
    missing_facets:
      - string
    route_level: R0 | R1 | R2 | R3 | R4 | R5

  owner_bundle:
    primary:
      - id: string
        paths:
          - string
        covered_facets:
          - string
        missing_facets:
          - string
    supporting:
      - id: string
        paths:
          - string
    truth:
      - id: string
        paths:
          - string
    verification:
      - id: string
        command_or_path: string
    excluded:
      - id: string
        reason: string
    bundle_level: B0 | B1 | B2 | B3 | B4 | B5

  coverage:
    required_facets_covered: boolean
    missing_required_facets:
      - string
    risk_surfaces:
      - string
    verification_available: boolean
    coverage_status: insufficient | inspect_ready | change_ready | release_ready

  permission:
    state: P0 | P1 | P2 | P3 | P4
    allowed_actions:
      - answer
      - ask
      - inspect
      - change
      - verify
      - finalize
      - learn_candidate
    blocked_actions:
      - string
    upgrade_requirements:
      - string
    downgrade_triggers:
      - string
    decision_reason: string

  final_claim:
    allowed_claims:
      - explain
      - likely_route
      - located
      - fixed
      - completed
      - release_safe
    blocked_claims:
      - string
    evidence_level: V0 | V1 | V2 | V3 | V4

  learning_candidate:
    aliases: []
    owner_bundles: []
    false_matches: []
    verification_priors: []
    memory_level: M0 | M1 | M2 | M3 | M4
    promotion_requirements:
      - string
```

Schema invariants:

```text
selected concept requires basis.
change requires P3+.
fixed/completed claims require verification result.
semantic-intake alone cannot produce P3.
learning above M1 requires evidence outside initial semantic intake.
```

## semantic-intake v1 API

`semantic-intake` 是 `project-cognition` 暴露给 Agent 的统一语义候选接口。它接收 Agent 抽取的 facets，返回受项目事实约束的 candidate universe。

推荐命令：

```bash
project-cognition semantic-intake --format json < intake.json
project-cognition semantic-intake --input intake.json --format json
```

Input:

```json
{
  "version": 1,
  "raw_request": "H5访问环境变量页面会出错，和客户端不太一样",
  "conversation_context": {
    "project_role": "downstream",
    "current_focus": "project-cognition routing precision",
    "prior_intent": null
  },
  "agent_facets": {
    "goal": {
      "required": ["investigate runtime exception"],
      "supporting": ["compare H5/client behavior"],
      "optional": []
    },
    "surface": {
      "required": ["H5/web", "environment settings page"],
      "supporting": ["settings UI"],
      "optional": []
    },
    "behavior": {
      "required": ["access exception"],
      "supporting": ["client/web difference"],
      "optional": []
    },
    "context": {
      "required": ["downstream project"],
      "supporting": ["upstream routing improvement"],
      "optional": []
    },
    "constraint": {
      "required": ["avoid generic weak match"],
      "supporting": [],
      "optional": []
    }
  },
  "options": {
    "payload_size": "M",
    "max_candidates": 8,
    "include_contrast": true,
    "include_rejected": true,
    "include_owner_hints": true,
    "include_verification_priors": true
  }
}
```

Output:

```json
{
  "version": 1,
  "readiness": "query_ready",
  "readiness_reason": [],
  "intake_summary": {
    "interpreted_surface_type": "ui_page",
    "interpreted_behavior_type": "runtime_exception",
    "ambiguities": [
      "H5 may mean mobile web or browser-hosted web surface"
    ]
  },
  "candidate_universe": {
    "primary_candidates": [
      {
        "id": "environment-settings-page",
        "labels": ["EnvironmentSettings", "环境变量设置"],
        "surface_type": "ui_page",
        "score": 0.86,
        "evidence_rank": "E2",
        "facet_coverage": {
          "covered": ["environment settings", "page access", "H5/web"],
          "missing": ["exact exception source"]
        },
        "owner_hints": {
          "primary_paths": ["desktop/src/pages/EnvironmentSettings.tsx"],
          "supporting_paths": [],
          "truth_paths": [],
          "verification_paths": []
        },
        "basis": [
          "page/access signals favor ui_page over config_surface"
        ]
      }
    ],
    "contrast_candidates": [
      {
        "id": "env-config",
        "labels": [".env", "environment variables"],
        "surface_type": "config_surface",
        "score": 0.43,
        "contrast_reason": "matches environment variables but not page access"
      }
    ],
    "rejected_candidates": [
      {
        "id": "workflow-environment",
        "surface_type": "workflow_surface",
        "false_match_type": "workflow-shadow",
        "rejection_reason": "workflow runtime does not match user-facing H5 page access"
      }
    ]
  },
  "expansion_targets": [
    {
      "id": "settings-route",
      "surface_type": "route_navigation",
      "purpose": "confirm route owner"
    }
  ],
  "missing_evidence": [
    {
      "facet": "exact exception source",
      "suggested_action": "inspect primary page owner and runtime stack"
    }
  ],
  "permission_hint": {
    "maximum_without_live_evidence": "P2",
    "blocked_actions": ["change", "root_cause_claim", "fixed_claim"]
  },
  "learning_candidate": {
    "memory_level": "M1",
    "aliases": [
      {
        "phrase": "环境变量页面",
        "concept_id": "environment-settings-page",
        "conditions": {
          "required_signals": ["页面", "访问"],
          "suppress_signals": [".env", "CI", "shell", "build"]
        }
      }
    ]
  }
}
```

Readiness values:

| readiness | Meaning | Agent behavior |
| --- | --- | --- |
| `query_ready` | Candidate universe is usable | Build RouteContract |
| `needs_semantic_intake` | Existing route is too weak and should be re-normalized | Re-extract facets and retry once |
| `needs_clarification` | Required user intent is missing | Ask one blocking question |
| `insufficient_index` | Index lacks enough project facts | Cap permission, suggest map update or targeted inspect |
| `stale_index` | Indexed facts appear outdated | Live evidence wins, mark stale |
| `runtime_unavailable` | Required capability is unavailable | Fallback to weak route hints |
| `error` | Runtime failure | Degrade safely, no change/final claim |

API non-responsibilities:

```text
does not call an LLM
does not read live source for investigation
does not edit files
does not run tests
does not decide final PermissionDecision
does not write confirmed/canonical learning
does not claim root cause or completion
```

## Agent Execution Protocol

Agent 在处理项目请求时必须遵守以下顺序：

```text
1. Intake
2. NeedContract
3. FacetSet
4. semantic-intake
5. RouteContract
6. OwnerBundle
7. CoverageContract
8. PermissionDecision
9. Allowed action
10. Verification
11. FinalClaim
12. LearningCandidate
```

旧 workflow 名称只作为 intent hint：

```text
sp-debug -> inspect-biased
sp-implement -> change-requested
sp-plan -> planning-biased
sp-review -> risk-focused
```

可以跳过 `semantic-intake` 的只有明确机械任务：

```text
运行一个用户指定命令
打开一个明确文件
解释用户贴出的具体代码
```

User-facing response 应简洁展示：

```text
我把目标理解为：...
当前主候选是：...
对照/排除项是：...
现在能做：...
现在还不能声称/不能做：...
下一步：...
```

Protocol invariants:

```text
No semantic-intake, no project-backed route.
No route, no owner.
No owner, no targeted inspect.
No coverage, no change.
No verification, no fixed/completed claim.
No evidence, no confirmed learning.
```

## PermissionDecision

`PermissionDecision` 决定当前可以执行什么动作，以及最终可以说什么。它不是用户意图，也不是 Agent 自信度，而是证据状态。

| State | Name | Required Evidence | Allowed Actions | Blocked Actions |
| --- | --- | --- | --- | --- |
| `P0` | `no-route` | Need 不清或无项目候选 | ask one blocking question | inspect broadly, change, finalize, learn confirmed |
| `P1` | `vocab-grounded` | 有词表/alias 候选，但无可靠 owner | answer likely candidates, request evidence | targeted code change, root cause claim, fixed claim |
| `P2` | `route-grounded` | 有 selected concept、初步 owner/expansion target | targeted inspect, refine route, explain current basis | change, fixed claim, completed claim |
| `P3` | `coverage-grounded` | required facets covered, owner bundle usable, verification owner exists | scoped change, run verification, update contract | broad change, release-safe claim |
| `P4` | `execution-grounded` | action verified, success signals satisfied, risk checks aligned | final claim, learning candidate, M2 promotion consideration | claims beyond verification scope |

Hard caps:

```text
semantic-intake only -> max P2
lexicon/keyword only -> max P1
no primary owner -> max P1
no verification owner -> max P2
stale generated launcher/runtime -> max P2 for affected workflow
insufficient index -> max P1/P2 depending on live inspect target
```

Claim matrix:

| Claim | Minimum Permission | Minimum Evidence |
| --- | --- | --- |
| `explain` | `P1` | vocabulary or route basis |
| `likely_route` | `P2` | selected concept + basis |
| `located` | `P2/P3` | primary owner + truth evidence |
| `fixed` | `P4` | positive + regression verification |
| `completed` | `P4` | all success signals satisfied |
| `release_safe` | `P4` | release-level verification and risk coverage |

Permission invariant:

```text
User urgency does not raise permission.
Agent confidence does not raise permission.
High candidate score does not raise permission.
Only evidence raises permission.
```

## LearningContract

`LearningContract` 定义哪些信息可以从一次任务中变成后续可复用记忆。它的目标是让系统越用越准，但不把错误推断固化。

Learning types:

| Type | Meaning | Example |
| --- | --- | --- |
| `alias` | 用户说法到项目概念的映射 | “环境变量页面” -> `environment-settings-page` |
| `owner_bundle` | 某类任务常见 owner 集合 | env page -> page + route + adapter + verification |
| `false_match` | 近似但应排除的候选 | “页面访问”时 `.env` 不应做 primary |
| `verification_prior` | 某类任务的验证路径 | env page -> page smoke/render test |

Memory levels:

| Level | Name | Meaning | Allowed Use |
| --- | --- | --- | --- |
| `M0` | transient | 当前会话临时理解 | 只影响当前 WorkContract |
| `M1` | candidate | 有路线依据但证据不足 | 下次弱提示，不可作为事实 |
| `M2` | confirmed | live evidence 或用户确认支持 | 可参与默认排序 |
| `M3` | reusable | 多次成功复用且无冲突 | 高权重候选 |
| `M4` | canonical | 稳定项目事实 | 核心词表/owner bundle |

v1 default:

```text
semantic-intake may output M1 learning_candidate.
v1 must not promote to M2/M3/M4 from semantic-intake alone.
```

Ambiguous phrases must not be unconditional aliases.

Bad:

```yaml
phrase: "环境变量"
concept_id: "environment-settings-page"
```

Good:

```yaml
phrase: "环境变量"
concept_id: "environment-settings-page"
conditions:
  required_signals:
    - 页面
    - 访问
  suppress_signals:
    - .env
    - build
    - CI
```

Learning invariant:

```text
Learning may bias future routing, but live evidence can always override it.
```

## Prompt and Template Sharing

统一语义能力必须通过共享 prompt partial 分发到所有 workflow 和 CLI 集成。不能只改某一个命令或某一个 Agent。

建议新增：

```text
templates/command-partials/common/semantic-work-contract.md
```

Shared partial 必须包含稳定锚点：

```markdown
<!-- SEMANTIC_WORK_CONTRACT_BEGIN -->
<!-- PERMISSION_GATED_ACTIONS -->
<!-- CONSERVATIVE_LEARNING -->
<!-- FINAL_CLAIM_GATE -->
<!-- SEMANTIC_WORK_CONTRACT_END -->
```

Required sections:

```text
1. Role Boundary
2. Unified Intake
3. WorkContract
4. semantic-intake
5. Permission-Gated Actions
6. Evidence and Final Claims
7. Conservative Learning
8. User-Facing Response
```

Sharing invariant:

```text
Semantic behavior belongs in shared partials and shared runtime contracts.
Integration-specific files may only adapt syntax, not semantics.
```

## Cross-CLI Requirements

统一语义工作合同是产品能力，不是某个 Agent 或某个 CLI 的局部优化。因此所有支持的 CLI / IDE 集成都必须遵守同一套语义规则。

What must be shared:

```text
WorkContract
FacetSet
semantic-intake call discipline
selected / contrast / rejected distinction
PermissionDecision P0-P4
FinalClaimGate
Conservative Learning rules
Workflow names as intent hints
```

What may differ:

| Area | Examples |
| --- | --- |
| File format | Markdown, TOML |
| Argument placeholder | `$ARGUMENTS`, `{{args}}`, `{{parameters}}` |
| Directory layout | `.codex/skills`, `.claude/commands`, `.gemini/commands` |
| Tool invocation syntax | shell command, MCP, IDE command |
| Subagent support | Claude Task, Codex multi-agent, none |
| Hook support | Claude/Gemini hooks vs instruction-only |

Invariant:

```text
A user should not get a different safety model because they use a different supported Agent.
```

## Scope Boundaries by Task Type

统一入口不要求用户选择任务类型，但系统内部会推断 `task_shape`。`task_shape` 只影响默认输出和风险判断，不改变路由协议。

| Task Shape | Mutation Intent | Requirements |
| --- | --- | --- |
| explanation | `none` | `P1/P2` 即可回答；不能编造未验证行为 |
| investigation | `inspect` | 至少 `P2` 才能 targeted inspect；定位结论需要 truth evidence |
| scoped_change | `change` | 必须先 route 到 owner；`P3` 才能改 |
| broad_change | `change` | 不能直接进入 `P3`；需要拆分子 WorkContract |
| verification | varies | 必须识别 positive/regression/risk checks |
| documentation | varies | 需要 truth owner 或 verified behavior |
| planning | varies | 需要 route 和 owner/risk surfaces；未知项要显式列出 |
| review | varies | 发现问题要绑定 evidence |

Rule:

```text
用户说“修”不等于 P3。
用户说“解释”不等于可以编造。
用户说“计划”不等于可以忽略 owner。
用户说“review”不等于可以跳过 project context。
```

## Data Model Mapping

v1 应优先复用 project-cognition schema v2 的现有表：

```text
metadata
generations
evidence
nodes
node_evidence
edges
edge_evidence
observations
observation_evidence
path_index
alias_index
updates
```

Mapping:

| Design Need | Schema v2 Surface |
| --- | --- |
| project concept | `nodes` |
| concept label / phrase | `alias_index` |
| concept relationship | `edges` |
| code path ownership | `path_index`, `node_evidence` |
| evidence source | `evidence`, `node_evidence`, `edge_evidence` |
| semantic intake record | `observations` |
| learning candidate | `observations` |
| promotion/downgrade/revoke | `updates` |
| generated/index version | `metadata`, `generations` |

Do not reintroduce broad old tables in v1:

```text
claims
claim_evidence
conflicts
conflict_claims
symbol_index
entrypoint_index
test_index
slice_members
query_examples
large FTS-only routing tables
```

Data model invariant:

```text
v1 changes should improve how existing graph/alias/evidence data is queried and packaged, not replace schema v2 with a new knowledge system.
```

## Runtime Scoring Model

`semantic-intake` 的分数不是纯文本相似度，也不是概率。它是用于候选排序的 evidence score，必须可解释。

v1 score components:

```text
alias_match_score
required_facet_coverage_score
surface_fit_score
owner_availability_score
false_match_penalty
evidence_rank_boost
```

Winner selection rules:

```text
covers required facets
surface type fits required surface
not blocked by false-match condition
has basis
```

If highest-score candidate violates required facets or surface type:

```text
move to contrast or rejected
select next valid candidate
or return needs_clarification/insufficient_index
```

Scoring acceptance:

```text
env-page-h5-error -> ui_page primary
env-config-not-applied -> config_surface primary
workflow-env-error -> workflow_surface primary
doc-only-question -> docs_reference_surface primary
```

Scoring invariant:

```text
The system must prefer the candidate that best satisfies required facets and surface type, not the candidate that sounds most similar.
```

## Readiness and Fallback Semantics

Fallback is not equivalent capability. Any fallback must reduce permission or disclose uncertainty.

| Value | Meaning | Agent Behavior | Permission Cap |
| --- | --- | --- | --- |
| `query_ready` | 候选宇宙可用 | Build RouteContract | From returned hint, max P2 without live evidence |
| `needs_semantic_intake` | 当前输入/旧 route 太弱 | Re-extract facets and retry once | P0/P1 until retry succeeds |
| `needs_clarification` | 缺少阻塞用户信息 | Ask one question | P0 |
| `insufficient_index` | 索引没有足够项目事实 | Suggest map update or targeted inspect | P1/P2 |
| `stale_index` | 索引可能过期 | Prefer live evidence, mark stale | P2 max until refreshed |
| `runtime_unavailable` | binary/command missing or incompatible | Fallback to weak route hints | P2 max |
| `error` | runtime failed unexpectedly | Degrade safely | P0/P1 |

Readiness invariant:

```text
When readiness decreases, permission must not stay the same unless live evidence independently restores it.
```

## Testing Strategy

测试目标不是证明某段 prompt 文案存在，而是保护统一语义入口的不变量：

```text
先形成 WorkContract
再获取候选宇宙
再判断证据和权限
再行动
再验证
再学习
```

Test layers:

```text
1. Runtime tests
2. Template rendering tests
3. Golden eval tests
4. Cross-integration consistency tests
```

Permission safety tests must be 100%:

```text
No semantic-intake-only result allows P3.
No case without verification owner is change_ready.
No case without verification result allows fixed/completed.
No M1 candidate is promoted to canonical.
No workflow-specific prompt bypasses permission.
```

Acceptance gates:

```yaml
runtime_tests: pass
template_rendering_tests: pass
golden_eval_cases: pass for critical seed cases
permission_safety: 100%
learning_non_promotion: 100%
cross_integration_anchors: 100%
```

Test invariant:

```text
A test should fail whenever a change makes the system more confident without adding evidence.
```

## Golden Eval Seed Cases

| ID | 用户输入 | Primary Surface | Primary Concept | Contrast | Rejected | Max Permission |
| --- | --- | --- | --- | --- | --- | --- |
| `env-page-h5-error` | H5访问环境变量页面会出错 | `ui_page` | `environment-settings-page` | `env-config`, `h5-client-boundary` | `workflow-environment` | `P2` |
| `env-config-not-applied` | 环境变量配了，但是启动后没生效 | `config_surface` | `env-config` | `environment-settings-page` | `workflow-environment` | `P2` |
| `build-env-missing` | 打包后环境变量没了 | `build_release_surface` | `build-env-injection` | `env-config` | `environment-settings-page` | `P2` |
| `workflow-env-error` | sp-debug 启动的时候环境报错 | `workflow_surface` | `generated-sp-debug-runtime` | `env-config` | `environment-settings-page` | `P2` |
| `client-h5-diff` | 客户端正常，H5不正常 | `adapter_boundary` | `web-client-boundary` | `ui_page` | `workflow-environment` | `P2` |
| `add-import-button` | 给环境变量页面加一个导入按钮 | `ui_page` | `environment-settings-page` | `import-feature-pattern` | `env-config` | `P2` |
| `env-page-learning` | 以后这种环境变量页面别再匹配到 .env | `workflow_surface` | `semantic-routing-rule` | `environment-settings-page` | `env-config-as-primary` | `P2` |
| `api-field-missing` | 保存的时候后端没收到这个字段 | `api_endpoint` | `save-api-contract` | `ui_form` | `docs-only-match` | `P2` |
| `state-lost-navigation` | 切页面之后状态丢了 | `state_store` | `navigation-state-store` | `route_navigation` | `build-env-injection` | `P2` |
| `doc-only-question` | 这个环境变量页面在哪个文档里说明了 | `docs_reference_surface` | `environment-settings-docs` | `environment-settings-page` | `env-config-as-primary` | `P1/P2` |

## Release and Compatibility

This capability affects runtime, generated templates, Agent prompts, Python launcher, and downstream projects. It must be released as a product surface, not just merged as source code.

Release assets:

```text
project-cognition binary
Python specify package
generated workflow templates
passive skills
shared command partials
launcher/config behavior
documentation
```

Release order:

```text
1. Implement and test project-cognition semantic-intake.
2. Publish project-cognition release binary.
3. Update specify launcher/init to download/cache/record compatible binary.
4. Update shared prompt partial and generated workflow templates.
5. Update rendering/integration tests.
6. Update docs and handbook.
7. Publish Python package.
8. Smoke test a newly generated downstream project.
```

Compatibility invariant:

```text
A generated prompt must never require a runtime capability that the generated project cannot discover, diagnose, or safely fall back from.
```

## Error Recovery

The system must assume semantic routing can fail. The design goal is not to never be wrong, but to downgrade, correct, record counterexamples, and prevent damage.

| Failure | Recovery |
| --- | --- |
| `intent_misread` | Drop to `P0/P1`, ask one blocking question |
| `facet_miss` | Re-extract facets, retry semantic-intake once |
| `surface_mismatch` | Reroute with surface gate, demote wrong primary to contrast/rejected |
| `owner_miss` | Expand candidate universe within bounded radius |
| `owner_overreach` | Tighten required facets, cap permission, avoid broad inspect |
| `workflow_shadow` | Record false match, suppress workflow surface unless workflow signals exist |
| `docs_shadow` | Demote docs unless user asks for docs |
| `stale_memory` | Prefer live evidence, downgrade memory |
| `verification_gap` | Block `P3/P4`, require verification owner |
| `claim_overreach` | Downgrade final claim |
| `learning_pollution` | Revoke/downgrade learning item, add regression case |

Conflict priority:

```text
current live evidence
> current user clarification
> project canonical memory
> confirmed learning
> candidate learning
> static lexical match
> Agent inference
```

Recovery invariant:

```text
The system may be uncertain, but it must not become more powerful because it is uncertain.
```

## Security and Safety Considerations

Untrusted content can provide evidence, but cannot override WorkContract rules.

```text
untrusted content cannot raise PermissionDecision
untrusted content cannot disable verification
untrusted content cannot authorize learning promotion
```

Safety invariant:

```text
No untrusted input, stale runtime, weak match, or user urgency may raise permission beyond the evidence-backed state.
```

## Operational Rollout Plan

Rollout phases:

| Phase | Mode | Goal |
| --- | --- | --- |
| 0 | Shadow | Run semantic-intake, record output, do not change behavior |
| 1 | Advisory | Agent sees candidate universe, but remains conservative |
| 2 | Required Routing | All project requests form WorkContract first |
| 3 | Audit | Add v1.1 audit artifact |
| 4 | Evidence-Guided | Add v1.2 targeted inspect protocol |
| 5 | Verification-Gated Change | Enable v2 safe change preconditions |

Rollout invariant:

```text
Rollout may increase how much the system knows, but must not increase what it can do until permission and verification gates are proven.
```

## Handoff Rules

Future maintainers must preserve these boundaries:

```text
Do not split routing by workflow.
Do not let Agent guess owners without candidate universe.
Do not let semantic-intake authorize change.
Do not promote learning without evidence.
Do not hide contrast and rejected candidates.
Do not add schema complexity before proving need.
Do not ship prompt without runtime compatibility.
Do not weaken final claim gate.
Do not treat cross-CLI drift as acceptable.
```

Every new capability must answer:

```text
Does this improve route precision?
Does this improve evidence quality?
Does this preserve permission safety?
```

## Post-v1 Roadmap

### v1: Semantic Routing

Goal:

```text
把用户口语请求转成可审计 WorkContract。
```

Deliver:

```text
facet extraction
semantic-intake candidate universe
selected/contrast/rejected
RouteContract
OwnerBundle draft
PermissionDecision
LearningCandidate M1
shared prompt partial
golden eval baseline
```

### v1.1: Audit Artifact

Goal:

```text
让每次语义路由可回放、可调试、可学习。
```

Add:

```text
WorkContract artifact
semantic-intake input/output snapshot
selected/rejected basis
permission upgrade/downgrade reason
action log
```

Current local status:

```text
minimal optional semantic-audit slice implemented
workflow-written semantic_audit_input schema defined in shared prompts
fixture coverage added for localized, mixed-language, symptom-first, false-friend, and stale-runtime cases
see universal-semantic-work-contract-handoff.md for the current release gate
```

### v1.2: Evidence-Guided Inspection

Goal:

```text
把 P2 targeted inspect 做成有证据目的的检查。
```

Add:

```text
inspection_plan
target -> missing facet mapping
live evidence capture
route rerank after inspect
stale index/memory downgrade
```

Current local status:

```text
minimal inspection_plan emitted by semantic-audit
missing facets and evidence needs map to bounded target_path or target_id
live_evidence_capture and rerank_after_inspect are explicit audit fields
stale_index_downgrade blocks broad reads when runtime or owner evidence is not trustworthy
workflow-captured live evidence feeds rerank_assessment
supporting live evidence creates only a non-granted permission_promotion_candidate
contradicting live evidence downgrades route permission and blocks further targeted inspect/change/final claims
owner_bundle_confidence summarizes indexed owner roles without treating them as live proof
owner_miss_expansion caps unresolved owner expansion at max_radius 1
route vocabulary evidence and unbounded broad source reads cannot create a permission promotion candidate
verification_owner_discovery reports indexed/missing verification owners and targeted_test candidates
verification_results can satisfy claim_readiness only when every selected candidate has a passed result matching an indexed verification owner path
failed verification results block claim_readiness with verification_result_failed until superseded by a newer matching passed rerun
blocked verification results block claim_readiness with verification_result_blocked until recovery or rerun produces a newer matching passed result
skipped or otherwise inconclusive verification results block claim_readiness with verification_result_inconclusive
workflow_authorization is explicit input/output and cannot be inferred from workflow name
workflow_authorization.active_claim_type records the single active final claim when multiple claims are authorized
multiple authorized claims without active_claim_type block claim_readiness with active_claim_type_required
active claims not listed in authorized_claims block claim_readiness with active_claim_not_authorized
root_cause_claim can become claim_ready only after bounded source evidence, matching passed verification for every selected candidate, status authorized, authorized_claims containing root_cause_claim, and a non-empty authorization_ref
fixed_claim, completed_claim, and release_safe can become claim_ready only with claim-specific passed verification for every selected candidate, top-level workflow_authorization status authorized, authorized_claims containing the claim, and matching claim_authorizations entries whose status is authorized, authorization_ref is non-empty, and verification_evidence_refs cover the matched verification results
claim_verification_refs records the verification evidence that supports the active claim
semantic_audit_state records semantic_audit_input_path, semantic_audit_output_path, semantic_audit_resume_status, active_claim_type, claim_readiness_status, claim_authorization_refs, and claim_verification_refs in workflow-state.md
semantic_audit_resume_validation compares selected_candidate_ids, active_claim_type, claim_authorization_refs, claim_verification_refs, and semantic_audit_route_fingerprint before trusting resumed claim readiness
semantic_audit_generated_resume_smoke and semantic_audit_stale_reasons record prompt-level generated resume smoke results before trusting persisted semantic-audit state
semantic-audit-resume/scenarios.md gives generated projects prompt-level examples for fresh and stale resume smoke outcomes
semantic-audit-resume provides an optional runtime JSON comparator for persisted audit input/output plus extracted workflow state; it records can_reuse_persisted_claim_readiness, grants_permission: false, and boundary: comparison_only_no_source_edit_or_claim_authorization; it does not grant P3/P4 permission or final claims
resume-validation.json and resume-validation-route-changed.json give generated downstream projects concrete semantic-audit-resume validator adoption fixtures
generated workflows prefer the optional runtime validator on resume by building an ephemeral resume-validation.json when the command is available, while preserving prompt fallback when unavailable or stale
active-claim, missing-file, claim-ref, and verification-ref stale fixtures give generated downstream projects executable semantic-audit-resume mismatch examples
real downstream resume smoke verifies workflow-local semantic-audit-input.json and workflow-local semantic-audit-output.json path resolution with ephemeral resume-validation.json
permission promotion above P2 remains deferred until a later workflow-specific permission contract exists
```

### v1.3: Verification Owner Discovery

Goal:

```text
在改动前稳定发现验证路径。
```

Add:

```text
verification_surface indexing
verification_prior scoring
positive/regression verification classification
no-verification downgrade rule
```

### v2: Safe Change Mode

Goal:

```text
证据充分时，统一入口可以做小范围修改。
```

Entry conditions:

```text
Route >= R4
OwnerBundle >= B4
Coverage = change_ready
Permission >= P3
Verification owner present
No required facet gap
```

### v2.1: Conservative Learning Promotion

Goal:

```text
把成功路线提升为可复用记忆。
```

Add:

```text
M1 -> M2 promotion
false-match writeback
conditional alias promotion
learning downgrade/revoke
updates audit
```

### v2.2: Downstream To Upstream Feedback

Goal:

```text
下游项目里的语义失败能反馈成上游改进。
```

Add:

```text
semantic failure report
upstream improvement candidate
auto-generated eval case
runtime/template compatibility diagnostic
```

### v3: Unified Autonomous Work

Goal:

```text
用户只说目标，系统完成理解、路由、执行、验证、学习闭环。
```

Add:

```text
automatic action mode selection
multi-agent owner verification
broad change decomposition
release-safe verification matrix
M3/M4 promotion with human/release evidence
```

Roadmap constraint:

```text
Do not skip v1.1 audit, v1.2 evidence-guided inspection, and v1.3 verification owner discovery before v2 safe change.
```

## Open Decisions Defaults

If no new evidence or explicit product decision overrides these defaults, implement this way:

| Decision | Default | Rationale |
| --- | --- | --- |
| API command name | `project-cognition semantic-intake` | 职责独立，避免混在 `compass` |
| API input | stdin JSON, optional `--input` | 方便测试，避免 shell 转义 |
| API output | versioned JSON | 可回归测试，可跨 CLI 使用 |
| Facet source | Agent-generated facets | Agent 擅长理解自然语言 |
| Runtime role | constrain and rank project-backed candidates | runtime 擅长项目事实和 deterministic 输出 |
| Live source reading | not in v1 semantic-intake | live inspect belongs after P2 |
| Embedding | optional recall aid, not winner authority | surface/facet gate 优先 |
| Learning write | M1 candidate only in v1 | 防止污染 canonical |
| Workflow names | intent hints | 保留兼容，不分裂语义路由 |
| Shared prompt | required across workflows/CLIs | 防止 drift |
| WorkContract artifact | v1.1 | v1 聚焦 routing，v1.1 做 audit |
| No semantic-intake fallback | cap permission at P2 | fallback 不是等价能力 |
| No verification owner | no `change_ready` | 防止无验证修改 |
| Ambiguous alias | conditional alias only | 防止“环境变量”等词污染 |
| Memory conflict | live evidence wins | 当前事实高于历史记忆 |
| Final claim | evidence-gated | 防止强话术弱证据 |

## Acceptance Criteria

Functional:

```text
A natural-language request can produce a WorkContract.
Agent extracts goal/surface/behavior/context/constraint facets.
semantic-intake returns primary/contrast/rejected candidates.
RouteContract includes basis and missing facets.
PermissionDecision caps action based on evidence.
LearningCandidate defaults to M1.
```

Safety:

```text
semantic-intake-only result never allows P3.
No verification owner means no change_ready.
No verification result means no fixed/completed claim.
No M1 candidate is written as canonical.
Workflow-specific prompts cannot bypass PermissionDecision.
```

Quality metrics:

```yaml
primary_owner_recall: ">= 90% on seed eval cases"
top_surface_accuracy: ">= 80% on seed eval cases"
false_match_detection: ">= 80% on seed eval cases"
permission_safety: "100%"
basis_required: "100% for selected concepts"
learning_non_promotion: "100%"
cross_integration_contract_anchors: "100%"
```

Final acceptance:

```text
v1 is accepted when the system can reliably turn colloquial project requests into project-backed, auditable, permission-bounded WorkContracts without allowing unverified action or irreversible learning.
```

## Review Checklist

Contract:

```text
[ ] Does the flow form WorkContract before inspecting/changing?
[ ] Are facets split into required/supporting/optional?
[ ] Are selected/contrast/rejected candidates present?
[ ] Does every selected concept include basis?
```

semantic-intake:

```text
[ ] Is the API versioned JSON?
[ ] Does it support stdin JSON?
[ ] Does readiness have structured output?
[ ] Is permission_hint capped at P2?
[ ] Is learning_candidate capped at M1?
[ ] Does semantic-intake avoid live source, edits, tests, and change authorization?
```

Permission:

```text
[ ] Is P0-P4 evidence-based?
[ ] Does semantic-intake-only stay below P3?
[ ] Does missing verification block change_ready?
[ ] Does failed/missing verification block fixed/completed?
```

Learning:

```text
[ ] Does v1 only produce/write M1 candidate?
[ ] Are ambiguous aliases conditional?
[ ] Are false matches typed and reasoned?
[ ] Is canonical promotion absent?
```

Red flags:

```text
[ ] Only sp-debug changed.
[ ] semantic-intake returns P3 or change_ready.
[ ] “环境变量” is unconditional canonical alias.
[ ] Highest score directly decides primary without basis.
[ ] Fallback broad-searches while keeping high permission.
```

## Implementation Readiness Notes

Required decisions before development:

```text
[ ] 命令名使用 project-cognition semantic-intake。
[ ] v1 不读 live source。
[ ] facets 由 Agent 生成，runtime 负责约束和排序。
[ ] semantic-intake 单独最高权限 P2。
[ ] v1 learning 默认 M1 candidate。
[ ] shared partial 跨所有 workflow/CLI 注入。
[ ] 旧 workflow 保留为 intent hint。
```

First implementation slice:

```text
semantic-intake command stub
versioned request/response types
stdin JSON parsing
deterministic candidate universe from existing alias/path graph
permission_hint max P2
M1 learning_candidate only
golden eval for env page/config/workflow
```

Implementation order:

```text
1. Define contracts
2. Add semantic-intake command stub
3. Add deterministic runtime scoring
4. Add golden eval fixtures
5. Add runtime tests
6. Add shared prompt partial
7. Inject partial into workflows
8. Add cross-integration rendering tests
9. Add fallback/stale runtime diagnostics
10. Update docs/help
11. Release project-cognition binary
12. Release Python package / generated assets
13. Smoke test downstream
```

Spec note:

```text
This document intentionally defines v1 and the post-v1 roadmap together. Do not implement v2 safe change behavior from this document until v1.1 audit, v1.2 evidence-guided inspection, and v1.3 verification owner discovery are complete.
```

## Traceability Matrix

| User / Product Need | Design Element | Verification |
| --- | --- | --- |
| 用户不想区分 debug/implement/plan | Unified Intake + workflow names as intent hints | 任意 workflow 都先形成 WorkContract |
| 用户表达口语化、多义 | Agent FacetSet | golden eval 覆盖中文、多义、混合表达 |
| 数据库是静态事实 | project-cognition candidate universe | semantic-intake 返回 project-backed candidates |
| Agent 能理解人话但不能乱猜 | Role Boundary | prompt/template 测试包含 “Agent is not project fact source” |
| “环境变量页面”不能误到 `.env` | Surface-aware scoring | env page vs env config eval |
| 近似误匹配要显式暴露 | contrast/rejected concepts | response 包含 contrast/rejected |
| 证据不足不能修改 | PermissionDecision P0-P4 | semantic-intake-only max P2 测试 |
| 无验证不能说修好了 | FinalClaimGate | fixed/completed claim 需要 verification result |
| 成功经验要复用 | LearningCandidate | M1 candidate 生成，M2+ 禁止 |
| 多 CLI 行为一致 | shared partial + rendering tests | cross-integration anchors |
| 下游发现的问题能回流上游 | v2.2 feedback | semantic failure report + eval case |

## FAQ

### Is this just better project-cognition search?

No. Search is only one part. The goal is a full contract:

```text
natural language -> WorkContract -> candidate universe -> permission-gated action
```

### Why not let Agent directly understand and search files?

Agent language understanding is strong, but project facts need evidence constraints. Without candidate universe and permission gates, Agent can confidently pick the wrong owner, miss verification, and learn wrong mappings.

### Why not make project-cognition understand all natural language?

That is not the right boundary. Agent handles natural language. `project-cognition` provides deterministic project facts, graph, paths, aliases, evidence, and observations.

### Why keep debug/implement/plan?

For compatibility. They become intent hints, not separate routing systems.

### Why cannot semantic-intake authorize change?

It only uses indexed candidate evidence. Change needs live evidence, owner coverage, and verification owner.

### Why keep contrast/rejected?

Because ambiguity and false matches are first-class routing evidence. Without them, the system cannot explain why `.env` was not selected and cannot learn suppression.

## Appendix: Canonical Example Fixture

```yaml
id: env-page-h5-error
description: H5/web access to environment settings page throws and differs from client behavior

raw_request: "H5访问环境变量页面会出错，和客户端不太一样"

agent_facets:
  goal:
    required:
      - investigate runtime exception
    supporting:
      - compare H5/client behavior
    optional: []
  surface:
    required:
      - H5/web
      - environment settings page
    supporting:
      - settings UI
    optional: []
  behavior:
    required:
      - access exception
      - client/web difference
    supporting: []
    optional: []
  context:
    required:
      - downstream project
    supporting:
      - upstream routing improvement
    optional: []
  constraint:
    required:
      - avoid generic weak match
    supporting: []
    optional: []

expected_semantic_intake:
  readiness: query_ready
  intake_summary:
    interpreted_surface_type: ui_page
    interpreted_behavior_type: runtime_exception

  candidate_universe:
    primary_candidates:
      must_include:
        - id: environment-settings-page
          surface_type: ui_page
    contrast_candidates:
      must_include:
        - id: env-config
          surface_type: config_surface
    rejected_candidates:
      must_include:
        - id: workflow-environment
          false_match_type: workflow-shadow

  required_basis_contains:
    - page
    - access
    - H5
    - ui_page

expected_work_contract:
  permission:
    max_without_live_evidence: P2
    blocked_actions:
      - change
      - root_cause_claim
      - fixed_claim
      - completed_claim

  learning_candidate:
    max_memory_level_without_live_evidence: M1

forbidden:
  - env-config_as_primary
  - workflow-environment_as_primary
  - permission_P3_without_live_evidence
  - fixed_claim_without_verification
  - canonical_learning_without_evidence
```

Expected user-facing summary:

```text
我把目标理解为：H5/web 访问“环境变量设置页面”时出现异常，并且需要比较它和客户端行为是否一致。当前主候选是环境变量设置页面；`.env` 配置只是对照候选，因为你说的是“访问页面”。workflow 环境不符合这个 surface，我会排除它。现在可以检查页面 owner、路由入口和 H5/client 边界；还不能判断根因，也不能直接修改。
```

## Appendix: Prompt Anchor Text Draft

```markdown
<!-- SEMANTIC_WORK_CONTRACT_BEGIN -->

## Universal Semantic Work Contract

You are the semantic mediator between the user's natural language and the project's cognition graph. Agent inference is not project fact. Project facts must come from project-cognition, live source/runtime evidence, or explicit user confirmation.

Do not require the user to choose debug, implement, plan, or review. Workflow names and command names are intent hints only. Every project request must first be interpreted through a WorkContract.

Maintain an internal WorkContract with:
- NeedContract
- FacetSet: goal, surface, behavior, context, constraint
- RouteContract
- OwnerBundle
- CoverageContract
- PermissionDecision
- FinalClaimGate
- LearningCandidate

Before mapping colloquial user language to files, owners, or implementation surfaces, keep the existing compass-first workflow: call `project-cognition compass` for the default brownfield intake, then call `project-cognition semantic-intake` when compass is draft-like, localized, symptom-first, mixed-language, missing coverage, or needs explicit concept decisions. Send the raw request, conversation context, extracted facets, and payload options. Use the returned candidate universe to build the RouteContract.

Do not choose a candidate only because it has the highest lexical or embedding score. Required facet coverage, surface type fit, owner evidence, false-match suppression, and basis are required.

A valid RouteContract distinguishes:
- selected concepts: current primary route candidates
- contrast concepts: similar but non-primary candidates
- rejected concepts: known or likely false matches

Permission states:
- P0 no-route: ask one blocking question only
- P1 vocab-grounded: explain candidates only
- P2 route-grounded: targeted inspect only
- P3 coverage-grounded: scoped change and verification allowed
- P4 execution-grounded: final claim and learning candidate allowed

`semantic-intake` alone cannot raise permission above P2. P3 requires live evidence, owner coverage, and a verification owner. P4 requires verification results.

Do not claim:
- located, without primary owner and truth evidence
- fixed, without positive and regression verification
- completed, without satisfying success signals
- release-safe, without release-level verification

Learning must be conservative, conditional, and reversible. v1 learning defaults to M1 candidate. Do not write confirmed or canonical learning from unverified inference. Use conditional aliases for ambiguous phrases.

When reporting to the user, summarize:
- interpreted target
- primary candidate
- relevant contrast/rejected candidates
- current allowed action
- blocked action or claim
- next step

Do not dump the full internal WorkContract unless the user asks.

<!-- PERMISSION_GATED_ACTIONS -->
<!-- CONSERVATIVE_LEARNING -->
<!-- FINAL_CLAIM_GATE -->
<!-- SEMANTIC_WORK_CONTRACT_END -->
```

## Appendix: Claim Wording Guide

| Evidence State | Allowed wording | Blocked wording |
| --- | --- | --- |
| `P0/V0` | 目前还缺一个关键信息 | 问题在某文件；我来修 |
| `P1/V1` | 我识别到几个候选方向 | 已经定位；根因是 |
| `P2/V2` | 当前主候选是；我会检查缺失证据 | 根因已确认；修复完成 |
| `P3/V3` | 证据支持做小范围修改 | release-safe |
| `P4/V4` | 已完成并通过验证；结论覆盖本次 owner bundle | 超出验证范围的结论 |

Claim rule:

```text
When evidence is partial, the claim must be partial.
```

## Appendix: Non-Regression Contract

Every future change must preserve these guarantees:

```text
A project request produces or updates a WorkContract.
Agent inference is not project fact.
project-cognition candidate universe constrains routing.
selected/contrast/rejected candidates remain distinct.
Surface type can override lexical similarity.
semantic-intake alone cannot exceed P2.
P3 requires live evidence, owner coverage, and verification owner.
P4 requires verification result.
User urgency cannot raise permission.
Workflow name cannot raise permission.
Agent confidence cannot raise permission.
located requires primary owner + truth evidence.
fixed requires positive + regression verification.
completed requires success signals satisfied.
release_safe requires release-level verification.
v1 learning defaults to M1.
M2+ requires evidence beyond semantic-intake.
Ambiguous aliases are conditional.
Generated assets must not require undiscoverable runtime capability.
Fallback must reduce capability or disclose uncertainty.
Cross-CLI generated prompts preserve shared semantic anchors.
```

Non-regression rule:

```text
A change that improves route recall but weakens permission safety is a regression.
A change that improves prompt fluency but hides contrast/rejected candidates is a regression.
A change that makes learning more aggressive without downgrade/revoke support is a regression.
A change that works in one CLI but weakens another CLI is a regression.
```

## Appendix: MVP Cutline

Must have:

```text
WorkContract v1 schema
semantic-intake v1 command
stdin/input JSON
versioned JSON output
primary / contrast / rejected candidates
surface-aware scoring
permission_hint max P2
LearningCandidate max M1
shared prompt partial
workflow names as intent hints
golden eval seed cases
permission safety tests
runtime unavailable fallback
```

Should have:

```text
owner_hints
expansion_targets
missing_evidence
basic false_match priors
readiness detailed reasons
cross-integration rendering anchors for all major CLI
downstream smoke test
README/help update
```

Must not have in v1:

```text
automatic scoped code change
M2/M3/M4 learning promotion
release-safe claim
full autonomous workflow
live source investigation inside semantic-intake
broad schema redesign
embedding as final winner authority
```

Cutline invariant:

```text
Never cut safety gates to save time. Cut automation first.
```
