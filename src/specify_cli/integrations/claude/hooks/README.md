# Claude Hook Assets

This directory contains the project-local Claude Code native hook assets that
`specify init --ai claude` installs into `.claude/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Claude-native hook events into the shared `specify hook ...` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.
