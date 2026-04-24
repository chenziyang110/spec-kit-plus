# AgentTeams 扩展集成计划 (Implementation Plan)

本文档是为后续开发者准备的落地指南。我们已经完成了扩展的基础骨架和声明文件，接下来需要您完成底层的源码搬运与核心状态机的联调。

## 1. 我们的目标
将 `oh-my-codex` 的沙箱多智能体调度能力（AgentTeams）以**源码级内置**的方式，作为一个完全解耦的插件集成到 `spec-kit-plus` 中。
- **无需用户全局安装** `oh-my-codex`。
- **按需编译**：用户首次运行时自动编译 Rust 和 TS 依赖。
- **工作流桥接**：截获 spec-kit 生成的 `tasks.md`，将其转换为底层的任务账本（JSON Ledger）并派发给多个独立沙箱。

---

## 2. 目前已完成的工作 (Extension Skeleton)
目前的 `extensions/agent-teams/` 目录下已经准备好了所有的外层壳子：
1. `extension.yml`：定义了前置依赖（tmux, rustc），并注册了挂载在 `after_tasks` 阶段的自动执行钩子。
2. `commands/run.md` 和 `cleanup.md`：AI 执行的入口命令。
3. `scripts/build-engine.sh`：负责在用户机器上首次拉起时执行 `npm install` 和 `cargo build`。
4. `engine/src/cli/bridge.js`：核心的转换层逻辑（目前包含基础的正则解析骨架）。
5. `engine/src/cli/cleanup.js`：负责清理异常退出的 Tmux Pane 和 Git Worktree。

---

## 3. 待实现的下一步任务 (Next Steps for Implementation)

请接手的开发者按照以下步骤，把真正的“肌肉”塞进这个扩展里：

### 步骤 A：底层引擎源码搬运
你需要从 `oh-my-codex` 项目中，把负责沙箱控制和状态编排的代码搬移到本扩展的 `engine/` 目录下：

1. **Rust 隔离引擎 (Muxer)**：
   - 将原项目的 `crates/omx-mux` 和 `crates/omx-runtime-core` 拷贝到 `extensions/agent-teams/engine/crates/` 目录。
   - 补充 `extensions/agent-teams/engine/Cargo.toml`，把上述 crates 组织为一个 workspace，并确保编译目标为 `omx-runtime`。

2. **TS 编排引擎 (Orchestrator)**：
   - 将原项目的 `src/team/` 目录及其相关依赖（如工具类）拷贝到 `extensions/agent-teams/engine/src/` 目录下。
   - 完善 `engine/package.json` 中的依赖项（例如 `yaml`, `tmux` 等第三方包），确保 `npm install` 能正常跑通。

### 步骤 B：完善桥接转换逻辑 (`bridge.js`)
目前 `bridge.js` 中只写了简单的正则表达式提取。你需要将其升级为：
1. **完整解析**：利用成熟的 Markdown AST（或增强正则）精准提取 `tasks.md` 中的多级任务及其依赖关系（`depends_on`）。
2. **生成标准账本**：将提取出的任务，按照 `oh-my-codex` 的要求，精确转换为 JSON Ledger 格式（必须包含 `id`, `role`, `status`, `input` 等字段），并保存到 `.specify/agent-teams/state/team/default/tasks/` 目录。

### 步骤 C：点火启动 Orchestrator
在 `bridge.js` 转换完任务后，它需要拉起 TS 状态机：
1. 替换 `bridge.js` 末尾的 `[Simulated]` 假执行。
2. 使用 `child_process.spawn` 拉起你搬运过来的 Orchestrator 入口（例如 `engine/src/team/runtime.ts` 的入口函数），并把配置的 `state_dir` 传给它。

### 步骤 D：角色与系统提示词 (Prompt Injection)
确保 Orchestrator 在启动 Worker Pane 之前，能够正确读取 `.specify/project-map/spec.md` 作为背景上下文，并将分配的角色指令合并写入到 `AGENTS.md` 沙箱环境中。

---

## 4. 联调与测试验证
完成以上搬运和修补后，你可以在任意 `spec-kit-plus` 项目中执行以下命令进行端到端测试：

```bash
# 触发引擎执行
/sp.agent-teams.run
```

**成功的标志：**
1. 终端显示 "Building AgentTeams Execution Engine"，并且成功编译出 Rust 二进制。
2. 自动切分出多个前缀为 `sp-team-` 的后台 Tmux session。
3. 多终端并行执行工作，可以通过 `tmux attach -t sp-team-...` 观摩。
4. 任务全部执行完成后，对应的 `worktree` 被自动合并回主分支并清理。
