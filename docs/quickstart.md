# Quick Start Guide

This guide will help you get started with Spec-Driven Development using Spec Kit.

> [!NOTE]
> All automation scripts now provide both Bash (`.sh`) and PowerShell (`.ps1`) variants. The `specify` CLI auto-selects based on OS unless you pass `--script sh|ps`.

## The 5-Step Process

> [!TIP]
> **Context Awareness**: Spec Kit commands automatically detect the active feature based on your current Git branch (e.g., `001-feature-name`). To switch between different specifications, simply switch Git branches.

### Step 1: Install Specify

**In your terminal**, run the `specify` CLI command to initialize your project:

```bash
# Create a new project directory
uvx --from git+https://github.com/github/spec-kit.git specify init <PROJECT_NAME>

# OR initialize in the current directory
uvx --from git+https://github.com/github/spec-kit.git specify init .
```

Pick script type explicitly (optional):

```bash
uvx --from git+https://github.com/github/spec-kit.git specify init <PROJECT_NAME> --script ps  # Force PowerShell
uvx --from git+https://github.com/github/spec-kit.git specify init <PROJECT_NAME> --script sh  # Force POSIX shell
```

### Step 2: Define Your Constitution

**In your AI Agent's chat interface**, use the `/speckit.constitution` slash command to establish the core rules and principles for your project. You should provide your project's specific principles as arguments.

```markdown
/speckit.constitution This project follows a "Library-First" approach. All features must be implemented as standalone libraries first. We use TDD strictly. We prefer functional programming patterns.
```

### Step 3: Create the Spec

**In the chat**, use the `/speckit.specify` slash command to describe what you want to build. Focus on the **what** and **why**, not the tech stack.

```markdown
/speckit.specify Build an application that can help me organize my photos in separate photo albums. Albums are grouped by date and can be re-organized by dragging and dropping on the main page. Albums are never in other nested albums. Within each album, photos are previewed in a tile-like interface.
```

### Step 4: Plan the Implementation

**In the chat**, move directly from `/speckit.specify` to `/speckit.plan` once the spec is planning-ready. This is the mainline workflow:

```bash
/speckit.plan The application uses Vite with minimal number of libraries. Use vanilla HTML, CSS, and JavaScript as much as possible. Images are not uploaded anywhere and metadata is stored in a local SQLite database.
```

Use `/speckit.spec-extend` only when an existing spec needs deeper analysis before planning.

### Step 5: Break Down and Implement

**In the chat**, use the `/speckit.tasks` slash command to create an actionable task list.

```markdown
/speckit.tasks
```

Optionally, validate the plan with `/speckit.analyze`:

```markdown
/speckit.analyze
```

Then, use the `/speckit.implement` slash command to execute the plan.

```markdown
/speckit.implement
```

When the feature touches an established boundary pattern in the target project, make that constraint explicit before coding starts:

- `/speckit.plan` should write an `Implementation Constitution` section instead of leaving the rule as background context only.
- Use `Implementation Constitution` for architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus.
- `/speckit.tasks` should turn those rules into explicit implementation guardrails before setup or feature work begins.
- `/speckit.implement` should treat those guardrails as binding execution constraints and confirm the owning framework, defining reference files, and forbidden drift before dispatching code-writing work.

> [!TIP]
> **Phased Implementation**: For complex projects, implement in phases to avoid overwhelming the agent's context. Start with core functionality, validate it works, then add features incrementally.

## Skill Map

After initialization, treat the generated commands as three groups:

- **Core workflow skills**: `/speckit.constitution`, `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`
- **Support skills**: `/speckit.map-codebase`, `/speckit.spec-extend`, `/speckit.checklist`, `/speckit.analyze`, `/speckit.explain`
- **Codex-only runtime**: `specify team` and `sp-team` when the project was initialized for Codex

Generated project navigation now follows the handbook system:

- Generated projects include `PROJECT-HANDBOOK.md` as the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- `.specify/project-map/status.json` records the current handbook freshness baseline and dirty state.
- After a successful `map-codebase` run, use `project-map complete-refresh` as the standard completion hook to record the fresh baseline.
- Any code change that alters navigation meaning must update the handbook system.

Use support skills when they solve a specific gap:

- `/speckit.map-codebase` when you are working in an existing codebase and need to generate or refresh the handbook/project-map navigation system before deeper workflow steps
- `/speckit.spec-extend` when an existing spec still needs deeper analysis before planning
- `/speckit.checklist` when you want to audit requirement quality after planning
- `/speckit.analyze` when you want a cross-artifact consistency check before implementation
- `/speckit.analyze` also flags boundary guardrail drift through `BG1`, `BG2`, and `BG3` when boundary-sensitive work was not preserved cleanly from plan to tasks to implementation guidance
- `/speckit.explain` when you want the current spec, plan, or tasks state restated in plain language

If you're starting from an existing codebase, run `/speckit.map-codebase` first so the brownfield navigation artifacts are fresh before requirement, planning, or implementation work continues. Downstream workflows use `.specify/project-map/status.json` to decide whether the existing map is fresh, possibly stale, or stale.

Use the lightweight routing rules consistently:

- `/speckit.fast` is only for trivial local fixes. Stay there only when the change is obvious, touches at most 3 files, and does not touch a shared surface.
- Upgrade to `/speckit.quick` when the work expands to more than 3 files, touches a shared surface, or needs research or clarification.
- `/speckit.quick` is for small but non-trivial work that still fits one bounded quick-task workspace.
- Quick workspaces live under `.planning/quick/<id>-<slug>/`, with `STATUS.md` as the source of truth and `.planning/quick/index.json` as a derived management index.
- Invoking `/speckit.quick` with no arguments should resume unfinished quick work when possible. If exactly one unfinished quick task exists, continue it automatically. `blocked` quick tasks remain resumable.
- Use `specify quick list`, `specify quick status <id>`, `specify quick resume <id>`, `specify quick close <id> --status resolved|blocked`, and `specify quick archive <id>` to inspect and manage quick tasks. `specify quick list` defaults to unfinished quick tasks.
- Upgrade to `/speckit.specify` when the request spans multiple independent capabilities, carries compatibility or rollout risk, or needs explicit acceptance criteria before implementation.

## Detailed Example: Building Taskify

Here's a complete example of building a team productivity platform:

### Step 1: Define Constitution

Initialize the project's constitution to set ground rules:

```markdown
/speckit.constitution Taskify is a "Security-First" application. All user inputs must be validated. We use a microservices architecture. Code must be fully documented.
```

### Step 2: Define Requirements with `/speckit.specify`

```text
Develop Taskify, a team productivity platform. It should allow users to create projects, add team members,
assign tasks, comment and move tasks between boards in Kanban style. In this initial phase for this feature,
let's call it "Create Taskify," let's have multiple users but the users will be declared ahead of time, predefined.
I want five users in two different categories, one product manager and four engineers. Let's create three
different sample projects. Let's have the standard Kanban columns for the status of each task, such as "To Do,"
"In Progress," "In Review," and "Done." There will be no login for this application as this is just the very
first testing thing to ensure that our basic features are set up.
```

### Step 3: Define the Plan

Once `/speckit.specify` reaches planning-ready alignment, move directly to `/speckit.plan`.

```bash
/speckit.plan We are going to generate this using .NET Aspire, using Postgres as the database. The frontend should use Blazor server with drag-and-drop task boards, real-time updates. There should be a REST API created with a projects API, tasks API, and a notifications API.
```

If an existing spec needs deeper analysis first, use `/speckit.spec-extend`.

```bash
/speckit.spec-extend Add sharper reporting requirements and cross-team notification expectations before planning.
```

### Step 4: Validate the Spec

Validate the specification checklist using the `/speckit.checklist` command:

```bash
/speckit.checklist
```

### Step 5: Define Tasks

Generate an actionable task list using the `/speckit.tasks` command:

```bash
/speckit.tasks
```

### Step 6: Validate and Implement

Have your AI agent audit the implementation plan using `/speckit.analyze`:

```bash
/speckit.analyze
```

Finally, implement the solution:

```bash
/speckit.implement
```

> [!TIP]
> **Phased Implementation**: For large projects like Taskify, consider implementing in phases (e.g., Phase 1: Basic project/task structure, Phase 2: Kanban functionality, Phase 3: Comments and assignments). This prevents context saturation and allows for validation at each stage.

## Key Principles

- **Be explicit** about what you're building and why
- **Don't focus on tech stack** during specification phase
- **Use `specify -> plan` as the default path**
- **Use `spec-extend` only when an existing spec needs deeper analysis before planning**
- **Validate** the plan before coding begins
- **Let the AI agent handle** the implementation details

## Next Steps

- Read the [complete methodology](https://github.com/github/spec-kit/blob/main/spec-driven.md) for in-depth guidance
- Check out [more examples](https://github.com/github/spec-kit/tree/main/templates) in the repository
- Explore the [source code on GitHub](https://github.com/github/spec-kit)
