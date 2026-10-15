# 从 sp-* 执行到正确 Project Cognition 的全链路优化方向

日期：2026-10-11。状态：方案与源码审计完成，本文提出的新增能力尚未实施。
范围覆盖 Classic、Advanced、原生 agent/worker、共享运行时、安装与实际消费者。

建议下一轮的主目标定为：**agent 把工作做对之后，用尽量少的额外操作，
把这次工作真正改变的项目事实更新正确，让下一个独立会话可靠地复用。**
既衡量交付正确性，也衡量认知更新正确性和完整闭环成本。

已有受保护的更新、失效、恢复和发布框架应继续复用。
首先补齐工作结果到认知事实之间的交接，再做有测量依据的局部提速。
减少提示词或增加记忆条数本身，都不能证明这个目标达成。

## 1. 本轮审计给出的基线

[上一轮实施与实测](2026-10-11-project-cognition-optimization-implementation.md)
证明了导航正确率 88/120 → 120/120，但总体任务耗时中位数为
17.196 → 19.088 秒，Classic 四种条件均退步。
前后测任务是导航，没有实际完成“修改或打包 → 更新认知 → 新会话消费”。
配对实验的 Learning 也都没有可用匹配记录。

因此，下一轮不能继续把找到正确文件、`update=ready` 或更多 capture 记录
当作整个闭环成功的替代指标。

本轮只读诊断仍得到 `unsupported_legacy_runtime`，Learning 返回缺少索引。
这说明本仓库的新源码实现和真实项目当前可消费的 map 是两项交付。
未来实施需要单独解决实际运行时、兼容性和 map 可用性；本轮未修改真实存储。

### 已有且应保留的基础

- 精确 workflow-owned 路径边界，重命名包含两端，不吸入其他任务的脏文件。
- planner 生成草稿和结构化执行参数，agent 只补它负责的语义和实际验证证据。
- 持久化更新意图、同锁更新与验证、幂等重放、摘要绑定的修复。
- `scope_ready` 与全项目 freshness/debt 分离。
- 受影响 claim 先失效；只有 claim-specific 证据才允许重新证明。
- Do 已有 session、definition epoch/digest、source fingerprint 和实际路径绑定。
- 新旧运行时能力检查、两种 profile 和跨集成渲染验证。

这些是当前能力，不应再次包装为从零建设的工作包。依据见
[共享 closeout 合同](../../templates/command-partials/common/inline-project-cognition-update.md)、
[closeout 执行 owner](../../tools/specify-runtime/closeout_apply.go)、
[Do 绑定](../../tools/specify-runtime/do_cognition.go)和
[claim reconciliation](../../tools/specify-runtime/internal/reconcile/prepare.go)。

## 2. 优先解决的具体断点

以下是静态源码和契约审计，不是已复现的运行时绕过漏洞。

| 断点 | 当前证据 | 对效率或正确性的影响 | 优先处理 |
| --- | --- | --- | --- |
| 收尾顺序与恢复动作不一致 | SPX Implement 276–283 行先说终结、随后 plan，又要求 apply 在终结之前；Quick 引用 38–39 行要求共享 closeout 后再写 receipt；共享合同 109 行禁止第二次写 | agent 可能先撞 gate、重复尝试或走过期恢复路径 | 从一个共享阶段/结果契约生成提示和 runtime 下一步动作 |
| worker 认知字段没有完整规范化消费链 | Classic implementer 173 行要求独立认知字段；`result.go` 429–452 行只保存固定字段，437 行不识别 `changed_paths` 别名 | 交接的结构化事实可能未进入规范结果，leader 收尾重新整理 | 现有 WorkerTaskResult 内定义并消费正式语义增量 |
| 增量登记完成与新语义补齐分离 | `store.go` 662 行将受影响 claims 标 stale；`state.go` 1203 行的 update ready 不要求这些语义重新得到证明 | 路径存在、更新可发布，仍可能缺少新的 owner/consumer/验证事实 | 将受影响事实义务及其处理结果接入收尾 |
| 通用验证与工作版本的绑定不如 Do 完整 | 通用 VerificationEvidence 为 command/result/artifact；Do 另有精确来源绑定 | 单纯 passed 文本不能证明验证对应最终修改及本次任务 | 将 Do 的绑定原则推广到已有 workflow owner |
| E2E 的提示合同与终结状态尚未形成同样强的绑定 | E2E 模板 710–719 行要求保留的测试资产变更更新 cognition；当前 close terminal 未见对应 cognition receipt 消费 | 模板要求需要进一步成为真实终结验收的一部分 | 仅对保留的真实变更绑定，不给只读测试制造更新 |
| scope 完成与入口 freshness 语义不完全一致 | cognition hook 可返回全局 partial 的 blocked；preflight 又把这些 errors 转为 warnings | 各入口实际如何降级、阻断或复用，需要统一与实测 | 基于任务依赖的相关性判断，保留全局债务 |

必须保留三个范围限定：

1. 通用结果已有 `observations/findings` 等语义通道，不能说任何语义都无法传递。
   Implement 的专用 normalizer 保留未知字段，但规范 changed-files 别名仍不含
   `changed_paths`。E2E 保留原始 `WorkerResultInput`，其 normalized 消费视图
   没有独立 typed cognition 字段，不能说原始输入永久丢失。
2. `typed_update.go` 307 行的空 content hash 属于 `workflow_update` 事件 evidence。
   现有 intent/delta、Do 和 claim-reconcile 各自已有绑定，不能推导全系统没有摘要。
3. 全局 validation、锁等待和重复闭包计算是待测成本点。尚未实测新的收尾性能，
   不能预先宣称它们就是总耗时的主因。

## 3. 目标闭环和“正确”的定义

下面是拟议的产品流程图，不是新的 CLI 名称或已实现状态机。

```mermaid
flowchart LR
    A[用户授权的 sp 工作] --> B[按需获取可用导航和经验]
    B --> C[原生执行与工作验收]
    C --> D[实际变更与证据归属]
    D --> E[分类并确定受影响事实]
    E --> F[补齐必要语义并校验绑定]
    F --> G[既有 closeout 与 reconcile owner 发布]
    G --> H[新会话真实查询和消费]
    H --> I[验证适用性并复用经验]
    I --> B
```

图中“发布”统指图内认知更新。具体实现保留既有失效、prepare/apply、
validate/finalize 的顺序和版本前置条件；不能绕过这些 owner 直接改数据库。

一次正确的认知更新，应能回答六个问题：

- **改了什么：** 实际属于本任务的新增、修改、删除、重命名和保留的失败修改是否完整。
- **对应哪个版本：** 工作输出、验证、语义证据和接受结果是否绑定同一版本。
- **事实是否成立：** owner、consumer、接口/状态契约、生成链、验证入口是否有对应证据。
- **旧事实如何处理：** 已删除的路径、别名、依赖和测试入口是否作废、替换或明确隔离。
- **哪里仍不确定：** 闭包截断、冲突和缺证据是否继续显示为未决，未受影响的证据是否保留。
- **下次能否用对：** 新会话能否找到正确入口，并避免依赖已过期答案完成下一项任务。

工作完成、范围内认知可用、全项目 fresh 必须分别表达。
`scope_ready` 加可见的无关全局债务，可以支持本范围闭环验收；
不能因为别处旧债务就要求每个任务全图重建，也不能把本范围完成写成全项目 fresh。
认知 `ready` 仍不授予修改权限，不设置工作流 `claim_ready=true`，不替代 Review/人类 Accept。
业务步骤成功但本范围仍需更新时，保留成功结果和精确恢复点，继续履行原工作流的关闭门槛。

## 4. 全部工作流采用分类合同

分类按实际效果及既有 owner 决定，不靠命令名或文件扩展名一刀切。
实施时要为全部 29 个 Classic 入口、30 个 Advanced 入口及 Advanced 安装的
Classic map 同伴建立逐入口映射；下表是设计分组，不是已完成逐入口接线的声明。

| 工作类型 | 典型入口/情况 | 应处理的认知义务 |
| --- | --- | --- |
| 只读与无实际变更 | ask、只读 review、仅执行已有测试、无变化检查 | 按需消费；不得制造假 mutation 或重复更新 |
| 规划和批准产物 | discussion/specify/plan/tasks/design/test-design/accept 等规划、审批行为 | 保留各自产物 owner；意图与审批不能自动成为“代码已实现”的事实，也不因此触发源码图更新 |
| 修改代码或项目契约 | implement/quick/fast/debug、review 修复 | 实际 delta、受影响语义、验证、发布、恢复都必须闭合 |
| 操作与构建交付 | do | 区分项目源/config 变更、构建输出、环境/外部系统结果；只有相关保留事实进入 cognition，其余归 Do/Playbook/Learning 对应 owner |
| 测试资产维护 | e2e 的保留测试、harness、config、相关文档变更 | 由 test-asset owner 提供准确变更，E2E 终结消费对应收据；只读执行和临时 trace 不自动入图 |
| 显式地图维护 | map-update、map-scan/build、spx-map-rebuild | 前者处理外部/遗漏/局部维修；后者只在既有重建条件或显式请求下运行 |
| 外部修改及未知格式 | 用户手改、其他工具修改、新 cohort/扫描策略 | 定期语义检查点核对实际差异；未掌握范围或格式时保留不确定性，不能因为没有 hook 就漏记 |

一项失败操作若留下真实保留修改，仍有失效和恢复义务；
一项成功构建若只产生临时二进制，则不能以“成功”作为写入源码图的理由。

## 5. 十个实施方向

### R0：先建立真正的闭环基线和实际可用入口

在现有评估工具上增加真实任务轨迹：从请求开始，经过执行、验证、
变更分类、认知更新、恢复，直到新会话消费。
保留所有拒绝和失败尝试，按阶段记录墙钟、原生调用、读写量、内存与锁等待。
模型 token 不可得时明确记为 unavailable，不用 stdout 字节替代。

另设实际安装/map 可用性行：检查固定运行时、能力和真实 status；
对缺失或不兼容基线走既有受保护的诊断、归档/重建合同，
在真实消费者入口证明可查询。不能把测试 fixture 成功当作用户已获得收益。
本方案本身不执行归档、重建、安装或发布。

R0 与 R1 并行的前提是：先冻结并独立接受 baseline 版本、fixture、任务和事实分母，
R1 在隔离候选环境修改。不能在同一份持续变化的工作树上采集所谓 before。
基线一旦变化，必须说明配对影响并重新接受相应输入。

### R1：统一收尾顺序、状态解释与恢复动作

保留一个共享合同，明确每个阶段的输入、合法结果、下一步和不可跳过的门槛，
由确定性模板/代码驱动两种 profile 和 runtime 返回的动作。
特别修正 Implement 的顺序冲突、Quick 的重复 receipt 和过宽 dirty fallback。

agent 常规路径只需：提供本任务事实与证据，消费 runtime 返回的执行动作和结果。
确定性的 update/validate/finalize/receipt 仍由共享 apply 管理。
已有持久 intent 必须 inspect/repair/replay；只有无法建立可信 intent 的情况
才用原有 dirty fallback。不能通过重打 receipt 或重建一个可用 map 来掩盖失败。

只保留必要的默认输出：当前 scope 结果、更新/失效数量、未决项、下一动作。
详细诊断按需展开，避免各命令输出并解释相同大段合同。

### R2：打通 worker → 结果保存 → leader → 更新草稿

在既有 `WorkerTaskPacket` / `WorkerTaskResult` 中增加正式、版本化的认知增量合同，
具体字段名需实现阶段由 schema owner 决定。语义至少包含：

- 实际修改路径和 rename 两端，以及对应任务、尝试和接受版本。
- 变化的行为、owner/consumer、生成物链及状态契约。
- 已确认的证据引用、需作废的旧事实、仍待核实的义务。
- 实际验证收据及适用范围，失败后仍保留的修改和恢复状态。

统一 normalizer、schema、提交、存储、读取和消费，不仅在 prompt 中多列字段。
leader 从已接受的结果和运行时观测的实际差异生成草稿；
失败/拒收 worker 留下的字节也要纳入失效核对，但不能被当作已接受事实。
多个 worker 的重叠、串行同文件版本和冲突必须合并或重新验证，不能最后写入者覆盖全部。

worker 可以提出语义候选，不直接发布全局图。
保持现有 Work/Activity 为权属来源，在现有生命周期保存可恢复输入，
不另建一套任务数据库或靠聊天记忆恢复。

### R3：让证据绑定到这次工作及最终版本

把 Do 已有的来源绑定原则推广到通用 closeout，而不是削弱 Do 来适配最小公共字段。
绑定已有工作身份/attempt、scope、实际 owned delta、源版本、验证收据和接受输出。
机械摘要、时间与完整性字段由运行时生成，agent 不手工伪造。

旧的 `command/result/artifact` 记录仍可作为兼容审计输入；
缺少所需版本绑定时，不得冒充新的强绑定证明。旧运行时缺少新能力时返回明确拒绝和恢复路线。
hash 证明输入输出一致，不证明命令真实执行、agent 身份或语义正确。
语义仍需独立验证对应源文件、真实行为和原验收条件。

验证后再次修改、跨任务复制 receipt、同大小同 mtime 字节变化、rename 和依赖变化，
都应使受影响绑定失效。只重验受影响后代，保留仍有效证据。

### R4：把路径更新接到受影响语义义务

planner 在完整变更分母上确定必须处理的事实：
owner、调用/消费关系、公开接口、配置/状态契约、生成链、验证入口及失效别名。
复用现有 affected closure、typed update 和 claim-reconcile。
路径事件只是起点；测试 passed 不能自动证明所有语义 claim。

稳定格式与注册规则负责确定性的提取和路径归属；agent 只处理不能机械决定的语义。
新增路径可以先维持 provisional；没有证据的事实继续 stale/unknown。
对已有精确 claim 用当前 reconcile prepare/apply，补齐才恢复对应状态。
不能用一段成功总结把整片受影响 claims 批量设为可信。

新组件、新行为产生的新 owner、edge 和 claim 还需要受控的新增与注册，
不能只依赖对既有 claim 的 reconcile。复用现有 scan/workbench、graph import/build
及 claim 编译 owner；先验证它们能否消费有范围的新增语义，必要时在这些 owner 内
扩展局部注册合同。该局部新增接线属于拟议实现，不能假定已有一个通用注册命令。
新增事实绑定当前证据、稳定身份和接受版本；注册或证据未闭合时仍为 provisional/未决，
不能借 update ready 宣称语义已补齐，也不能因此每次隐式调用全量 map 工作流。

更新后针对变化的 owner/consumer/验证入口做真实查询，并加入旧路径、旧别名、
已删除调用或测试的反例。轻量消费者检查不要求每次全仓重跑，也不能替代完整发布前评估。

### R5：按相关范围决定可用性和更新规模

扩展既有 scope/global 区分到任务消费端：依据本次读依赖、写范围及受影响关系，
判断已有 debt 是否真的相关。相关性不确定时保守降级或扩大核对，不默认为无关。
这需要逐一验证 hook、preflight、无 hook 集成和各命令真实入口；
不能把所有 `blocked` 简单删掉，也不能把 warnings 当作已经统一的保护。

更新规模采用四类策略，均为拟议 planner 分类，不是新的 CLI 状态：

| 分类 | 判断依据 | 处理方式 |
| --- | --- | --- |
| 无认知变化 | 实际没有受管理事实变化，且按 owner/policy 能证明 | 不新增图 mutation；原有 source-changing no-op 的验证合同仍保留 |
| 局部变化 | 有完整可证的路径和依赖闭包 | 更新必要路径及事实，保持其他证据与导航缓存 |
| 传播变化 | 接口、生成规则、依赖、状态或共享配置有影响 | 扩大到真实消费者闭包；截断与未知项保持可见 |
| 基线不可用 | 缺失、不兼容 schema、身份失真或既有明确重建条件 | 走受保护的重建/恢复 owner，不能把普通失败升级为全量清空 |

### R6：在不减弱正确性检查的前提下减少更新成本

先测 R0 阶段数据，再依收益逐项实现：

- 从同一份观测复用 Git delta、文件摘要、变更分类和必要闭包；
  接受/提交边界仍确认当前内容和依赖，不能仅凭 mtime 缓存判正确。
- 多个独立 worker 在现有验收 join 批量合并更新；实际源变化应及时失效，
  不能等待批量发布期间仍把旧语义作为当前事实。
- 研究用“既有全局证明 + 本次完整增量证明”减少重复全图验证。
  无法证明局部完备、规则/基线变化或碰到截断时回退完整验证。
- 将可复用的昂贵准备放在提交之前，提交时在既有锁内重验版本前置条件。
  冲突则拒绝/重算；不能为了缩短持锁时间拆掉原子性。
- 对无变化消费和重复任务复用现有 capsule/Expand；变化或约束漂移才升级读取。
  Learning 适用性仍独立核对，不借 graph generation 假定它也新鲜。
- 原始日志与可复核证据在 owner 管理的存储保留，agent 默认只读摘要和匹配条目。
  长期证据去重与保留规则要单独验证，不能静默删除失败历史。

验收按 profile 分开看完整任务耗时，减少 SQL、字节或提示长度不能单独过关。
批处理及锁优化还应测共享 claim、旧 intent、冲突重试和独立 scope 的等待，防止饥饿。

### R7：让重复工作的收益来自可验证的持久经验

明确三类已有 owner 的职责：

| 层 | 保存什么 | 成为可复用依据的条件 |
| --- | --- | --- |
| Project Cognition | 当前项目结构与事实、关系、证据、未知项 | 对应当前源版本与依赖，已失效事实不能冒充当前答案 |
| Project Learning | 为什么失败、适用约束、可复用教训 | 真实证据、适用范围、反例检查；确认与提升沿用显式 promote 合同 |
| Playbook | 经过验证的操作方法、参数和恢复路径 | 已有不可变方法版本、环境/输入适用性及真实执行结果 |

不要把一次成功推广成全项目规则，也不要把所有源码事实复制到 Learning。
重复/同类任务先检查适用性，匹配就复用；不匹配则保留理由并回到当前源证据。
过期、矛盾或在新版本失败的经验应降低可用性或回到待核验，不自动提升。
普通 workflow 不绕过 Playbook 发布 owner 自造方法库。

收益实验要分开“同会话记忆”和“跨会话持久收益”：
首轮真实任务 → 新会话精确重复 → 未见过的同类变体 → 项目变化后再次执行。
使用相同 cognition 条件，比较无 Learning、真实匹配候选、按既有合同显式确认的经验。
加入错组件、旧版本和矛盾经验负例，禁止把评分答案提前写进记忆。

### R8：把完整闭环做成不可缩水的验收集

保留上一轮 120 条导航案例作为回归，但另建完整闭环分母。
每个必需案例包含：原始用户任务、业务验收、实际变更、应变化/失效的事实清单、
精确接受版本、更新结果、新会话真实消费及全部失败恢复证据。

至少覆盖以下案例族，并在对应两种 profile 下运行：

1. 只读/无变化、输出型操作：没有假更新或无谓图写入。
2. 普通修复、新增、删除、重命名：两端和旧别名、consumer、验证入口处理完整。
3. 跨组件接口、配置、生成模板、依赖变更：传播闭包完整且不污染无关范围。
4. Implement/Quick/Debug/Review 修复、Do 项目变更、E2E 保留资产：使用各自真实入口和 owner。
5. 验证后再改、旧证据串用、已接受输出被修改：拒绝旧绑定并重开受影响消费者。
6. 多 worker、串行同文件、共享 claim、互不相交 scope：合并、冲突和权属行为可复现。
7. 在准备、更新、语义 reconciliation、验证和 receipt 边界中断：幂等恢复、历史保留、无假 fresh。
8. scope_ready 加无关 global debt、相关 read dependency debt：既不误放行，也不伪造全局完成。
9. 外部工具/用户修改、未知格式、缺失/旧基线：降级与恢复路线真实有效。
10. 相同/同类任务的跨会话复用和过期经验负例：实际完成下一项任务，不能只看命中数。

主指标是完整闭环一次成功率、错误事实被接受数、漏失效数、应更新事实召回率、
误更新率、完整尝试耗时，以及待刷新积压/陈旧窗口。
事实精度和覆盖率分别报告，不能删掉难例提高分数。
关键固定反例集合要求零错误接受；这不是普遍零错误保证。

性能从请求到“业务完成且本范围认知可消费”计时，并单列新会话消费者段。
失败、重试、恢复、人工等待不能消失；不能相加重叠的并行 episode 冒充总工作时间。
两种 profile 独立验收，不让 Advanced 的改善掩盖 Classic 退步。
保持相同仓库、难度、事实分母和模型设置，交叉执行新旧版本；冷/热缓存分别注明。
先小样定位，再扩样讨论尾延迟；性能预算在基线后、候选评估前固定，不能看结果后改门槛。

作者、语义验证者和最终消费者分离。验证者直接读最终源码、原任务和完整事实清单；
runtime 自己返回 ready、worker 自报成功、一条绿色测试或哈希一致都不足以独立验收。

### R9：完成跨 profile、跨集成和真实分发接入

shared runtime、schema、artifact/result owner、Classic partial/passive/worker prompts、
Advanced shared/owning references、hooks、安装能力和帮助文档必须一起传播。
Advanced 安装的 Classic map 同伴继续保持字节等价；不安装 Classic passive bundle。

对应的 schema、两 profile、渲染、安装能力宣告和兼容接线必须随 R1–R7 的 owning
工作包一起落地并验收。R8 使用实际渲染、安装的候选入口完成闭环，不能只调用
独立运行时或检查模板源码。R9 负责已整合版本的分发级验证与真实消费者落地，
不是把这些必要接线推迟到最后。

验证 fresh install、两种 profile 叠加、升级/修复、自定义文件保护、旧运行时能力拒绝、
真实 Windows/POSIX 脚本和代表性有/无 hook 集成。
当前三项平台未验边界不能因方案完成而改为通过。
本地测试、云 CI、公开发布和匿名消费者验证分开记录；实际发布另走既有分发授权和合同。

## 6. 可执行工作包与依赖

下面是未来实施的完整方向分母，10 个工作包；不是本轮“已实施”清单。
实施时逐包展开验收行，固定原范围与新增范围，保留失败、缺口和输出版本。

| ID / 顺序 | depends_on | 责任 owner | 必需输入 → 输出 | 包级验收 |
| --- | --- | --- | --- | --- |
| R0 / P0 | 无 | 评估工具、运行时/安装诊断 | 原始任务与当前环境 → 闭环基线、成本分段、实际 map 可用性路线 | 全尝试计时、完整事实分母、真实入口状态，未验环境明确 |
| R1 / P0 | 无，可与 R0 并行 | shared closeout、生成器、runtime 恢复输出 | 当前合法阶段/动作 → 一致的两 profile 合同与下一步 | 不重复 receipt、不错误降级 intent、不先终结后更新；拒绝/恢复可复现 |
| R2 / P0 | R1 | WorkerTaskResult/schema、各提交/消费 owner | worker 与实际变更 → 无损规范结果及 leader 更新草稿 | Implement/Quick/E2E 真正提交再读，字段/别名/失败修改完整 |
| R3 / P1 | R2 | 共享 closeout、workflow/Do/E2E owner | 接受结果和源版本 → 通用版本绑定及兼容拒绝 | 串证据、再修改、错 scope/attempt 均拒绝；Do 原约束保留 |
| R4 / P1 | R3 | planner、typed update、scan/import/claim/reconcile/validation | 完整 delta → 受影响义务、新事实注册、已证事实与未决项 | 应更新/失效分母完整，新组件及 owner/consumer/测试入口可查询，旧答案不被误用 |
| R5 / P1 | R4 | query/status、preflight/hooks、scope owner | 依赖与债务 → 相关范围可用性 | 无关债务不被清掉，相关/未知债务不被绕过，各入口一致 |
| R6 / P2 | R0,R3,R4,R5 | update/validation/store/cache | 已测成本与正确性基线 → 批处理、复用、局部验证候选 | 两 profile 的质量不退；原子性和故障恢复保留；完整成本达预设预算 |
| R7 / P2 | R3,R4 | Learning/Playbook/既有工作 owner | 真实结果与教训 → 有适用性证据的复用 | 不自动 promote；新会话及变体有效，错误/旧经验能拒绝 |
| R8 / P2 最终汇合 | R0–R7 | 独立验证和消费者 | 各已接受输出 → 完整闭环报告及可复核证据 | 全案例分母、失败恢复和平台缺口公开，无自证、无性能泛化 |
| R9 / P3 | R8 | render/install/release owner | 已接受整体版本 → 集成产物和真实消费者验证 | 两 profile/代表性集成/旧 runtime 拒绝正确；分发完成需单独证据 |

每包自产的测试应随包执行，R8 是最终跨包汇合，不是把验证全部推迟到最后。
生产者输出通过独立验收后，消费者绑定对应版本再开始；输出变化则重开受影响后代。
源代码变更和用户当前项目的修复属于不同写入范围，实施时分别登记，不能隐式混做。

优先落地 **R1 + R2 + R3**：先让 agent 按一致顺序，把已经做过且验收过的工作
无损交给 cognition。随后 **R4 + R5** 保证认知确实反映新事实且可被正确消费。
**R6 + R7** 再优化端到端成本与长期复用收益，R0 的测量贯穿全程。

## 7. 源码依据索引与证据边界

本表行号对应本轮已有工作树；之后源码改变应重新核对。
本轮没有重跑产品测试，没有复现 gate 绕过，也没有实施 R0–R9。

| 事实 | 当前 owner 与行号 |
| --- | --- |
| 共享更新、语义失效/reconcile、scope/global、恢复、唯一 receipt | [inline-project-cognition-update.md](../../templates/command-partials/common/inline-project-cognition-update.md)：3–122 |
| Quick 重复 receipt 指令 | [validation-and-closeout.md](../../templates/command-references/quick/validation-and-closeout.md)：35–43 |
| SPX Implement 次序冲突 | [SKILL.md](../../templates/advanced-skills/spx-implement/SKILL.md)：276–286 |
| Runtime 提示 standalone receipt | [implement.go](../../tools/specify-runtime/implement.go)：213–224；[quick_cognition_closeout.go](../../tools/specify-runtime/quick_cognition_closeout.go)：133–143 |
| Worker 语义交接与规范化字段 | [implementer.md](../../templates/worker-prompts/implementer.md)：171–173；[result.go](../../tools/specify-runtime/result.go)：160–184、429–452；[quick_result_validation.go](../../tools/specify-runtime/quick_result_validation.go)：11–18 |
| Implement 保留未知字段、changed-files 别名边界 | [implement_tasks.go](../../tools/specify-runtime/implement_tasks.go)：1229–1251 |
| E2E 原始输入、终结和 normalized result | [e2e_workflow.go](../../tools/specify-runtime/e2e_workflow.go)：149–150、555、760–829、1157、2027–2040；[e2e.md](../../templates/commands/e2e.md)：710–719 |
| Path provisional adoption、事件 evidence、claim stale | [typed_update.go](../../tools/specify-runtime/internal/store/typed_update.go)：91–178、295–310；[store.go](../../tools/specify-runtime/internal/store/store.go)：643–665 |
| 通用 verification、前后 closure、ready 分层 | [state.go](../../tools/specify-runtime/internal/update/state.go)：36–40、920、973、1203–1229 |
| Do 来源绑定、实际 scope、复核 | [do_cognition.go](../../tools/specify-runtime/do_cognition.go)：14–46、81–124 |
| Hook blocked 与 preflight warnings 的区别 | [project_cognition.py](../../src/specify_cli/hooks/project_cognition.py)：27、136–153；[preflight.py](../../src/specify_cli/hooks/preflight.py)：14–21 |
| 同锁更新/验证及已有故障覆盖 | [closeout_apply.go](../../tools/specify-runtime/closeout_apply.go)：157–267；[closeout_apply_test.go](../../tools/specify-runtime/closeout_apply_test.go)：256、326、375、474、625、668、858、907 |
| 两 profile 和源维护边界 | [Workflow Profiles](../agent-guidance/workflow-profiles.md)；[Workflow and Runtime Maintenance](../agent-guidance/workflow-maintenance.md) |

审计由 workflow 与 runtime 两条独立只读线完成，并相互核验关键发现；
评估方向另经独立检查。方案审阅验证方向、完整性与源码依据，
不代表 R0–R9 的实现或性能收益已经通过验收。
