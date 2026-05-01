> **Note:** `context-loading-gradient.md` now defines the shared atlas hard
> gate. This file remains only as a compatibility shim for templates not yet
> migrated to the same contract.

- Check whether `.specify/project-map/index/status.json` exists.
- If it exists, use the project-map freshness helper for the active script
  variant to assess freshness before trusting the current handbook/project-map
  set.
- [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by
  `/sp-map-build` before continuing, then reload the generated navigation
  artifacts.
- [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths
  and reasons plus `must_refresh_topics` and `review_topics`. If the current
  task intersects `must_refresh_topics`, run `/sp-map-scan` followed by
  `/sp-map-build` before continuing. If only `review_topics` intersect, review
  those topic files before deciding whether the atlas remains sufficient.
- Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
- Check whether the required handbook/project-map outputs for the current atlas
  contract exist.
- [AGENT] If the navigation system is missing, run `/sp-map-scan` followed by
  `/sp-map-build` before continuing, then reload the generated navigation
  artifacts.
- Treat task-relevant coverage as a coverage-model check, not just a
  file-presence check.
- [AGENT] If task-relevant coverage is insufficient for the current request,
  run `/sp-map-scan` followed by `/sp-map-build` before continuing, then
  reload the generated navigation artifacts.
