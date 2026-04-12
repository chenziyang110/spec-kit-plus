# Technology Stack: context-aware bug fixing (`sp-debug`)

**Project:** spec-kit-plus
**Researched:** 2026-04-12

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | >=3.11 | Core Runtime | Matches existing project infrastructure. |
| Typer / Click | ^0.12 / ^8.1 | CLI Framework | Existing project standard for command handling. |
| Rich | ^13.0 | TUI / Formatting | Used for beautiful CLI outputs and status bars. |

### AI & LLM Interaction
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LiteLLM or OpenAI SDK | Current | LLM Orchestration | Provide a unified interface for multiple models (GPT-4o, Claude 3.5 Sonnet). |
| Markdown | N/A | State Persistence | Human-auditable, version-controllable, and fits existing Spec Kit patterns. |

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Git | N/A | State Checkpointing | Enables "atomic reverts" of debug sessions. |
| Bash / PowerShell | N/A | Tool Execution | To execute reproduction scripts and test suites. |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Instructor | N/A | Structured Data | If we need to parse specific sections of `DEBUG.md` into Pydantic models. |
| Pathspec | ^0.12 | File Filtering | To respect `.gitignore` when scanning codebase for context. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| State Store | Markdown | SQLite / JSON | Markdown is more transparent to developers and integrates with Git history natively. |
| Orchestration | LiteLLM | LangChain | LangChain is often considered too "heavy" for a focused CLI tool like `sp-debug`. |

## Installation

\`\`\`bash
# Core dependencies (already in project)
pip install typer rich litellm pyyaml

# For debugging/development
pip install pytest pytest-cov
\`\`\`

## Sources

- `pyproject.toml`
- [LiteLLM Documentation](https://docs.litellm.ai)
- [Rich Documentation](https://rich.readthedocs.io)
