# Project Cognition 优化审计与实施建议

日期：2026-10-10。范围：当前源码、实际安装提示、隔离运行时样本与优化设计。
本报告完成的是审计和方案，下面的产品修改尚未实施。

## 结论

优先修复导航命令与缓存新鲜度，再减少查询装配、无效翻页和重复上下文加载。
已有架构可以继续使用；主要收益应来自让现有能力正确、按需地协作。
目标是降低完成真实任务的总成本，同时保持找对 owner、覆盖必要消费者和验证真实结果的准确率。

三类知识继续分工：Cognition 提供当前项目的候选导航，Learning 保存可复用教训，
Do/Playbook 保存已经验证的操作方法。重复任务应更快定位、更少重复探索，
但每次执行仍需检查当前适用条件和实际结果。

## 已有能力与本轮边界

当前已实现并应保留：

- Schema v5、alias catalog、精确 concept/path 绑定、CJK 语义消歧。
- Compass 最多 3 条 lane、15 个首读路径，以及按需展开和目录分页。
- 同一请求中复用 cognition capsule 与 Learning intake；该能力已有，消费者仍有不一致。
- claim 生命周期、完整风险汇总、revision 约束的 reconciliation、事务化增量更新。
- 内容、策略、契约和依赖范围绑定的扫描缓存，以及相同构建输入的复用。
- 图仅提供导航候选；源码、测试、配置和实际运行证据才证明当前事实。

本仓库本地诊断返回旧 schema 1，当前运行时要求 schema 5。
`status` 拒绝；Compass 虽有成功的外层调用状态，内层仍为 blocked，且没有可用首读路径。
本轮没有迁移、删除或重建真实图，也没有直接解析其数据库。
这属于本 checkout 的状态，不能据此推断所有已安装项目都不可用。
本地 Learning 索引缺失同样只是本地验证边界。

## 已证实的问题

### 1. Advanced 的展开命令不可执行

`templates/advanced-skills/_shared/project-cognition.md:75` 使用 `expand --ref`，
而 `tools/specify-runtime/internal/cli/cli.go:2028` 只接收 `--id`、`--section` 和 `--format`。
真实 Codex Advanced sh/ps 安装中的 62 份共享引用保留了错误参数。
两次实际执行均以退出码 2 拒绝；改用 `--id` 后正常完成参数解析。
后者在没有对应 bundle 的隔离项目中返回 missing expansion，并不等于展开成功。

修正提示，使其消费 `expansion_ref.id` 与选定的可用 section；
增加安装产物到真实参数解析器的契约测试。无需为错误提示新增运行时别名。

另有旧库错误信息建议直接 remove/archive 数据库，见
`tools/specify-runtime/internal/runtime/status.go:181` 与
`tools/specify-runtime/internal/store/store.go:206`。
应统一指向已有的 `cognition archive-incompatible-store --inspect`，
消费它返回的摘要绑定归档参数，再按既有授权边界进入 map 工作流。
修改错误文案不意味着自动执行恢复，也不能绕过原来的拒绝条件。

### 2. 同一 generation 内变化未使旧 Expansion 失效

`internal/query/expansion.go:141` 比较 generation，`:280` 的 bundle 身份由
query fingerprint、generation 和两个 contract version 组成。
当前契约确实只声明 generation 失效，缺少同代 mutation/claim revision 绑定。

隔离反例：Compass 生成 bundle 后，通过原 store owner 将 claim 标记 stale；
旧 Expand 仍返回 `status=ok`、`state=supported`、`freshness=fresh`。
重跑 Compass 后，同一个 expansion ID 的内容变为 stale。

这会误导后续导航，但尚未证明绕过最终声明或修改授权：返回值仍保留
`usable_with_review` 和必须核对实时证据的约束。

建议由现有查询和存储 owner 定义一致的导航快照版本，覆盖所有相关同代修改入口。
先保证相关变化可靠失效，再评估更细粒度的复用。
bundle 身份应绑定内容或对应 revision；发布使用原子写，禁止同 ID 静默更换语义。
Expand 在变化时返回明确的 stale 状态和重新查询动作。

### 3. 返回一页之前仍装配整张图

`internal/query/lexicon.go:150` 和 `internal/query/compass.go:294` 加载全部候选；
`internal/store/store.go:1557` 的装配对每个节点继续查询路径、别名、证据 ID、
证据路径和观察摘要，随后才筛选或分页。
目录的输出分页已经存在，但没有限制这段后台装配工作。
不能概括为所有 query 都如此：已有精确绑定分支不应被错误地算作全图查询。

本轮使用当前实现、隔离 schema v5 图，固定每页 10 张卡片，每项顺序测量 5 次：

| 节点数 | 目录首屏中位耗时 | 目录中间页中位耗时 | Compass 中位耗时 | 首屏 JSON 字节 |
| --- | ---: | ---: | ---: | ---: |
| 30 | 9.42 ms | 9.80 ms | 10.29 ms | 4,905 |
| 300 | 61.44 ms | 60.08 ms | 63.25 ms | 4,920 |
| 1,000 | 274.05 ms | 277.88 ms | 264.49 ms | 4,935 |

这是现状基线，不是优化后的收益。测量是进程内 owner 调用，包含打开存储及
Compass 原有展开文件写入，排除 fixture 建立、CLI 启动与末尾 JSON 编码。
未清理操作系统缓存，可能有并行检查干扰；5 个样本不足以宣称稳定 P95。
候选装配的逐节点 SQL 次数由源码推导，没有冒充 SQL profiler 实测计数。

优先批量装配所需表数据，保持完整候选排序与语义规则。
无查询文本的 catalog 使用稳定顺序的真实分页读取，并保留总数、缺口和版本绑定。
语义搜索不能在排序前随意用 SQL LIMIT 截掉候选，造成速度变快但漏掉正确 owner。
证据及观察字段若参与现有排序，不能未经等价性验证就延迟加载。

### 4. 首选 lane 可能没有具体 claim 证据

`internal/store/store.go:800` 对全部候选的 claim 详情使用
`ORDER BY c.id LIMIT 25`，详情获取发生在最终 lane 确定之前。

27 条 claim 的反例中，字典序靠前的弱候选耗尽配额，最高排名 lane 的
`claim_refs` 为零，展开结果也没有目标 claim。
完整生命周期汇总仍正确标记其 stale 并要求 reconciliation；问题是缺少可操作的详情，
不是过期风险被隐藏，也不是安全声明被放行。

先保留完整生命周期汇总，再按选中的 lane 分配详情配额，优先呈现相关风险。
同时给出总数、已返回数量、截断说明和精确继续读取入口，保持响应有界。

### 5. 提示消费者仍有额外调用与加载风险

- `src/specify_cli/integrations/base.py:1024` 对普通 Implement 要求仅在引用过期、
  缺失或被反证时再调 Compass；`:4469` 的 Teams 提示仍要求分派前执行。
  应统一当前范围、必要 facets、证据和版本不变时的复用规则。
  已证实的是提示差异，尚未测得真实 agent 的重复调用次数。
- Advanced 共享 cognition 提示要求在 `has_more` 时继续遍历 catalog；
  Classic 及 Advanced map-build 已有按需继续规则。
  应在所有必需 facets 有有效精确绑定、负约束和歧义已处理后停止翻页；
  找到第一个词面匹配不等于覆盖完整，没有有效绑定时仍必须继续或报告缺口。
- Advanced 共享文件为 18,685 字节、297 行，其中收尾部分文本约 8,650 字节。
  小型只读 Ask 也要求读取这个共享文件。
  19 个 Classic semantic sidecar 经真实 include resolver 展开后合计 637,018 字节，
  单个约 32–54 KB；源文件是 include wrapper，并非手工维护的重复副本。
  这些是条件加载材料的静态尺寸，不能相加当作单次任务输入或实际 token 消耗。

保留短的必读导航与安全规则，将精确语义解析、修改收尾、恢复细节按明确触发条件加载。
按实际调用和读入材料评估收益，不设置脱离任务契约的行数或 token 硬上限。

### 6. 扫描有请求内重复哈希路径，收益尚待测量

`internal/scanworkbench/scanworkbench.go:284` 与 `scan_cache.go:578` 的部分
非 exact-resume 路径会为 fingerprint 和缓存选择分别整文件读取、计算同一路径摘要。
扫描缓存已经存在，不应重新建设一套。

先记录各路径读取次数、字节和分配，再决定是否共享一次请求的安全内容观测、
或对大文件使用流式哈希。不能把不同安全阶段的两次重验无条件合并，
不能依赖长期 mtime 缓存，接受或发布前的实时内容约束必须保留。

## 建议工作包与依赖

所有工作包当前均为待实施。R/W 编号用于对应本轮发现，不能作为产品已完成的声明。

| 工作包 | 优先级 / 对应发现 | 主 owner | 依赖 | 必须通过的验收 |
| --- | --- | --- | --- | --- |
| C0 可执行命令和受控恢复 | P0；WF-5、RT-01 | Advanced shared、CLI/status/store 错误输出、安装契约测试 | 无 | 两 profile 实际安装命令可解析；恢复只提供受控 argv；摘要漂移、路径逃逸、目标冲突仍拒绝 |
| C1 导航快照失效 | P0；RT-02 | query/expansion、compass、现有 store mutation/reconciliation owner | 冻结当前反例与基线 | 同代 stale/reconcile/rename/delete、generation 变化、损坏 ID 和契约版本均正确处理；同 ID 不覆盖不同语义；并发发布无半文件 |
| C2 lane 证据配额 | P1；RT-04 | store claim 查询、compass、claim_signal | 冻结 27-claim 反例；消费 C1 当前版本 | 首选 lane 有相关 claim ID；大候选不能挤掉其他选中 lane；完整风险汇总、截断与继续入口保留 |
| C3 批量装配与真实分页 | P1；RT-03 | store 候选装配、lexicon、compass、相关 query 分支 | 基线与 C1 版本契约 | 候选、排序、字段、路径和缺口与原行为对照一致；遍历无丢失/重复；测量 SQL、分配、字节和耗时 |
| C4 统一按需调用 | P1；WF-1、WF-2 | integration renderer、Classic passive/common、Advanced shared/map | C1 的有效性依据；C6a 基线 | 未变 preparatory calls 不触发重复 intake；全部 facets 绑定后不强制遍历余页；变化/歧义/缺口仍刷新和扩展 |
| C5 按触发加载提示 | P1；WF-3 | 两 profile 自有引用和渲染 owner | C0；完整有效契约清单 | 只读任务少加载无关收尾内容；修改、恢复和 resume 必需内容仍可达且触发；实际安装和渲染覆盖 |
| C6a 任务级基线 | 前置；WF-4 | workflow-quality 评测、独立事实验证者 | 无 | 冻结任务、预期 owner/消费者、环境与原始调用记录；明确冷启动和重复条件；产出可重放基线包 |
| C6b 重复任务回放与经验复用 | P2；WF-4 | 现有 Learning/cognition/Playbook 消费者与评测 owner | C6a；C1–C5 验收结果 | 同类第二次/后续执行减少无效探索；独立正确率不退化；源码/目标/约束变化使旧经验被重验或拒绝 |
| C7 扫描读取优化 | P2；RT-05 | scanworkbench fingerprint/cache | 证明读取成本有实质影响 | 同大小/同 mtime 内容变化、读取后替换、路径重定向、跨路径依赖、策略变化及恢复均正确；再报告 I/O 与内存收益 |

C0 与 C6a 可先独立完成。C1 是任何扩大缓存复用前的正确性前提。
C2 与 C3 同属 store/query，实施时应拆开提交并串行接受，避免交叉修改掩盖回归。
C4/C5 可由不同的明确文件 owner 准备，但共享引用和 renderer 的修改必须在合并点串行验证。
每项由未作者输出的验证者对原验收集检查，变化后重开受影响的依赖验收。

## 怎样证明“越用越快、越用越准”

先冻结任务级基线，再实施并在同一组输入上比较。
选取定位代码、解释功能、排查问题、编译打包入口、测试入口五类任务，
每类包含中文/项目术语、跨模块和容易走错的样本。
由独立验证者依据当前源码冻结正确 owner、必要消费者、验证入口和应拒绝的错误路线，
不能让被评测图自己生成自己的正确答案。

每个任务覆盖首次执行、原样重复、同类变体、源码变化四种条件，
另加入目标目录、generation、claim revision、权限或约束变化的负例。
两 profile 使用同一事实和验收标准。
试验阶段至少采用 5 个任务族、每族一个样本、每条件 3 次独立运行，
即每 profile 60 条观测；这只是发现问题的最小试验，不足以宣称稳定尾延迟。
记录并固定被比较运行的源码/runtime 摘要、模型和配置、工具权限、硬件及冷热条件；
源码变化条件记录确切变更，不能把有意变更混入相同输入对比。
正式效果判断应增加独立样本和重复次数；样本不足时不报告 P95。

记录：

- 找到第一个经实时证据确认的正确 owner 所需时间，以及完成整项任务的总时间。
- 实际 Compass、Learning、catalog、query、expand 调用数，源文件读数及重复读数。
- 实际输入/输出字节；仅在可获得真实模型统计时报告 token，不能把字节等同 token。
- 必要 owner/消费者/验证入口覆盖率、错误路线率、过期复用率和安全拒绝结果。
- 冷启动与后续重复分别统计；更换数据和路线也能适用的改善才算同类任务收益。

已有 Learning 可保存路由错误、有效查询策略、验证线索和避免误导的教训，
已有 reconciliation 修正具体图 claim，已有 Playbook 复用经过验证的操作方法。
下一次只加载匹配知识，核对当前适用条件；被反证的建议不能因历史使用次数多而加权升级。
仍通过原 capture/promote owner 处理记录，不因每次运行就生成一条教训，
不自动提升为项目规则，也不新增平行记忆数据库。

## 复现与验证范围

测量环境为 Windows、Go 1.26.1、Python 3.13；当前工作区含此前已接受的 Do/E2E 修改。
产品源码未因本轮审计改变。测试图为独立临时项目，使用现有
`internal/query/query_test.go` 的 `queryTestPaths`、`seedReadyGraph` 和 Store API。
没有将 fixture 的图断言冒充真实仓库事实。

规模测量复现方法：在 query 包的临时 Go overlay 测试中，分别导入 30/300/1,000 个节点。
每节点使用一个唯一标题 `route%06d`、一个 `src/module-%06d.go` 路径和一个来源证据，
由现有 fixture helper 补齐别名并发布 ready metadata。
分别以 `Mode=catalog, Limit=10, Offset=0`、`Offset=N/2` 调用 `LexiconWithOptions`，
以 `Intent=explain, Query=route000007` 调用 `Compass`，每组 5 次。
只对 owner 调用计时，调用后编码 JSON 计算字节；断言目录返回 10 项、总数等于 N，
Compass 路径非空且不超过 15。此次共 45 次测量，无跳过或失败。

准确性反例的复现步骤：

1. 建立一条 supported/fresh claim，Compass 后通过原 `MarkClaimsStale` 修改它，
   保持 generation 不变；读取旧 bundle，再次 Compass，比较 claim 状态和 ID。
2. 建立 27 条匹配 claim，使弱候选的字典序靠前并占满 25 项配额，
   目标强匹配 lane 包含 stale claim；比较完整风险汇总、lane refs 与展开详情。
3. 在实际安装的 Advanced 共享引用中提取错误 `--ref` 调用，送当前运行时解析；
   正确 `--id` 对照仅用于区分参数失败和缺少 bundle，不能算实际展开成功。

作者完成 2 个当前行为反例和 31 个现有顶层 Go 回归（17 个子测试），
工作流侧完成 8 项相关 Python 契约测试。
独立验证者复跑 2 个反例及相关控制，共 6 个顶层、2 个子测试；这些数量存在重叠，
不能相加当作独立测试总数或全库回归结果。
本轮对测量所用 1,735 个保守源码/脚本绑定做了完整性核对，
其中包括依赖包未必参与本次编译的测试源，不能称为精确编译输入数量。

关键源码摘要，便于判断本报告是否已过期：

| 文件（相对 `tools/specify-runtime`，另有注明） | SHA-256 |
| --- | --- |
| `internal/store/store.go` | `3eee6af23f89fd839ff56b0d496896b0f1ae30763330bdbed845a48c0fd58621` |
| `internal/query/compass.go` | `cd794ec6916abd39079b98354f7dcca112025377eb9429c746255cbd60dc1d8c` |
| `internal/query/lexicon.go` | `8bb0de3e5b400cb10ddf8d41675129c32656197d2a965f0578dea4cf4217464f` |
| `internal/query/expansion.go` | `4c0d3e90fc131d8dcf046f43b669082571a19d8961643031060b11b26a98b2bd` |
| 仓库根下 `templates/advanced-skills/_shared/project-cognition.md` | `f3a10afc1ce3ef1ff926420094774f667bdb5a067e04d174ec4217317bfa8bb4` |
| 仓库根下 `src/specify_cli/integrations/base.py` | `fa62187b295bcf8aa163f6a073ef845ea76932dc80136db1e667029768c94cf6` |

尚未验证：方案实施后的速度/准确率收益、真实完整 agent 任务回放、Linux/macOS、
其他宿主实际加载、云 CI、发布和公开消费者。
后续涉及共享运行时或提示修改时，必须同步 Classic/Advanced、受影响的安装/修复/打包、
旧运行时能力拒绝、精确绑定及恢复测试；发布仍是独立授权和验证范围。
