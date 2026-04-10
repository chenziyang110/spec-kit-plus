# Feature Specification: Codex Team Runtime Import

**Feature Branch**: `001-codex-team-adapter`  
**Created**: 2026-04-10  
**Status**: Draft  
**Input**: User description: "把 oh-my-codex 的 tmux 多智能体 team/runtime 那一套直接并入 spec-kit-plus，第一期只对 Codex CLI 开放，其他 AI CLI 不受影响。"

## Scope Boundaries *(mandatory)*

### In Scope

- 将 oh-my-codex 的 team/runtime 核心能力以源码级方式纳入 `spec-kit-plus` 仓库维护
- 为 `--ai codex` 项目默认安装并启用 team/runtime 相关能力与入口
- 在首发阶段将这套能力限制为仅对 Codex integration 可见和可用
- 为后续其他 AI CLI 的差异化适配保留扩展边界，但不在本期交付这些适配
- 为已有 Codex 项目保留可选升级路径设计空间，但不把它作为首发硬承诺

### Out of Scope

- 为 Claude、Gemini、Copilot、Cursor 等非 Codex integration 提供首发 team/runtime 入口
- 将首发范围收缩为仅外部依赖调用或仅规格占位，不实际并入源码
- 在本期内完成所有非 Codex agent 的产品化接入、行为验证和文档承诺
- 将已有 Codex 项目的迁移成功率作为首发版本的硬验收条件

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 启用 Codex 团队能力 (Priority: P1)

作为使用 `specify init --ai codex` 的项目维护者，我希望初始化后的项目默认具备以 `specify` 自身入口暴露的团队执行能力，这样我不需要额外接入外部工具或学习外部命令表面。

**Why this priority**: 这是首发范围的核心价值，决定“并入成功”是否真正对 Codex 用户可见。

**Independent Test**: 在一个新初始化的 Codex 项目中，仅验证 team/runtime 能力相关入口已通过 `specify` 自身表面默认安装、可发现、且其他 integration 不会获得同类入口。

**Acceptance Scenarios**:

1. **Given** 用户执行 `specify init --ai codex`，**When** 初始化完成，**Then** 项目中应默认包含通过 `specify` 自身入口可用的 team/runtime 能力
2. **Given** 用户执行非 Codex integration 初始化，**When** 初始化完成，**Then** 项目中不应生成这套 Codex 专属入口

### User Story 2 - 在仓库内维护运行时能力 (Priority: P2)

作为本仓库维护者，我希望这套团队运行时能力以源码级方式并入并由本仓库维护，这样后续针对 Codex 的功能增强和缺陷修复不依赖外部项目演进。

**Why this priority**: 这是用户明确指定的产品边界，直接影响实现 ownership、发布方式和后续演进速度。

**Independent Test**: 检查仓库内存在正式维护的 team/runtime 能力模块与发布路径，并且首发验收要求覆盖启动、分发、状态记录、失败提示与收尾清理。

**Acceptance Scenarios**:

1. **Given** 仓库维护者查看实现边界，**When** 审核首发方案，**Then** 能确认 team/runtime 核心能力属于本仓库正式维护范围
2. **Given** 首发版本进入验收，**When** 进行最小真实运行验证，**Then** 应能验证启动、分发、状态记录、失败提示与收尾清理这五类闭环能力

### User Story 3 - 隔离非 Codex 集成影响 (Priority: P3)

作为多 integration 产品维护者，我希望这次并入不会改变其他 AI CLI 的默认行为，这样可以先控制首发风险，再逐步做其他 CLI 适配。

**Why this priority**: 这是首发阶段最关键的兼容性约束，决定发布风险是否可控。

**Independent Test**: 对同一版本分别初始化 Codex 与非 Codex 项目，确认只有 Codex 项目拥有 team/runtime 相关入口与默认能力。

**Acceptance Scenarios**:

1. **Given** `--ai codex` 与其他 `--ai` 初始化结果对比，**When** 检查生成产物，**Then** 只有 Codex 项目带有首发 team/runtime 能力

---

### User Story 4 - 控制旧项目升级承诺 (Priority: P4)

作为产品维护者，我希望首发版本优先保证新初始化的 Codex 项目可用，而不是把已有项目升级成功作为硬门槛，这样可以控制首发范围和交付风险。

**Why this priority**: 这直接影响发布承诺和任务拆解，但优先级低于新项目默认可用和运行闭环。

**Independent Test**: 检查首发规格与对齐报告中是否明确区分“新项目硬承诺”和“旧项目升级可选支持”。

**Acceptance Scenarios**:

1. **Given** 维护者审阅首发范围，**When** 检查迁移策略，**Then** 能确认已有 Codex 项目升级不是首发硬承诺

### Edge Cases

- 当用户在不支持 team/runtime 的 integration 中尝试寻找相同入口时，系统如何明确告知该能力尚未开放？
- 当用户已有旧版 Codex skills 项目时，新增默认能力如何避免产生重复入口或不一致行为？
- 当用户所在环境缺少 tmux 或不属于首发支持环境时，系统如何明确阻止进入首发能力路径？
- 当团队运行过程中出现派发失败或运行时异常时，系统如何给出可验证的失败提示并保持可清理状态？
- 当已有 Codex 项目尝试升级但未完全满足新能力前置条件时，系统如何避免被误认为首发失败？

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 以源码级并入方式将 team/runtime 核心能力纳入 `spec-kit-plus` 的正式维护范围
- **FR-002**: 系统 MUST 在 `specify init --ai codex` 时默认安装并启用首发 team/runtime 能力
- **FR-003**: 系统 MUST 使首发 team/runtime 能力仅对 Codex integration 可见和可用
- **FR-004**: 系统 MUST 保持其他 AI integration 的默认初始化结果不因该能力而发生行为变化
- **FR-005**: 系统 MUST 为未来其他 AI CLI 的专门适配保留明确的扩展边界，但不得在本期默认开放这些入口
- **FR-006**: 系统 MUST 以 `specify` 自身的命令与技能表面向 Codex 用户暴露该能力，而不是以 `omx` 或 `$team` 作为正式产品入口
- **FR-007**: 系统 MUST 在首发规格中将 tmux 定义为必需运行依赖，并仅对具备 tmux 的环境作出功能承诺
- **FR-008**: 系统 MUST 在检测到缺少 tmux 或处于非首发支持环境时，向用户提供明确且一致的不可用反馈
- **FR-009**: 系统 MUST 为首发版本定义接近完整闭环的验收要求，至少覆盖团队启动、任务分发、状态记录、失败提示与收尾清理
- **FR-010**: 系统 MUST 将“新初始化的 Codex 项目默认可用”定义为首发硬承诺
- **FR-011**: 系统 MUST 不将已有 Codex 项目的升级成功定义为首发硬验收条件
- **FR-012**: 系统 MAY 为已有 Codex 项目提供升级路径，但该路径在首发版本中属于可选支持而非发布阻塞项

### Key Entities *(include if feature involves data)*

- **Codex Team Capability**: 针对 Codex integration 首发开放的团队执行能力集合，包含 `specify` 自身入口、运行时能力与相关安装结果
- **Integration Capability Boundary**: 用于区分 Codex 首发能力与其他 integration 默认行为的产品边界规则
- **Imported Runtime Surface**: 从 oh-my-codex 思路中并入本仓库维护的团队运行时能力表面
- **Existing Codex Project Upgrade Path**: 面向既有 Codex 项目的可选升级路径，用于描述如何获得新能力，但不作为首发硬承诺

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% 的 `specify init --ai codex` 新项目默认具备可发现的、基于 `specify` 自身表面的首发 team/runtime 入口
- **SC-002**: 100% 的非 Codex integration 初始化结果不生成首发 team/runtime 相关入口
- **SC-003**: 仓库维护文档与规格中对首发范围、非目标集成边界和后续扩展空间的描述保持单一且无冲突
- **SC-004**: 维护者能够在一次发布说明中清晰说明“已并入、仅 Codex 首发、其他 CLI 不受影响”这三个结论
- **SC-005**: 100% 的不满足首发运行环境条件的场景都会得到明确的不可用说明，而不是进入模糊或半可用状态
- **SC-006**: 首发验收中可对启动、分发、状态记录、失败提示与收尾清理五类闭环行为分别给出可验证结果
- **SC-007**: 首发说明中能够明确区分“新项目默认可用”与“旧项目升级可选支持”，且不存在相互矛盾的描述

## Assumptions

- 首发版本允许先围绕 Codex 用户群体定义产品能力，再逐步扩展到其他 AI CLI
- “直接抄进来”在本规格中解释为源码级并入并由本仓库负责维护，而不是运行时继续依赖外部项目安装
- 首发支持环境以具备 tmux 的环境为准，不承诺无 tmux 平台的等价体验
- 旧项目如需升级，可在后续版本或附加流程中支持，但不构成首发阻塞条件
