> **Note:** Commands that include `context-loading-gradient.md` use layered loading and should NOT also include this file. This file is retained for commands not yet migrated to the layered model.

- Check whether `.specify/project-map/index/status.json` exists.
- If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
- [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
- [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current request, run `/sp-map-scan` followed by `/sp-map-build` before continuing. If only `review_topics` are non-empty, review those topic files before deciding whether the existing map is still sufficient.
- Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
- Check whether `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md` exist.
- [AGENT] If the navigation system is missing, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
- Task-relevant coverage is insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- Treat task-relevant coverage as a coverage-model check, not just a file-presence check.
- [AGENT] If task-relevant coverage is insufficient for the current request, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
