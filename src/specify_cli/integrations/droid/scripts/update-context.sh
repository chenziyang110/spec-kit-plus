#!/usr/bin/env bash
# Update project context for Factory Droid through the shared renderer.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")" && pwd)"
while [ "$repo_root" != "/" ] && [ ! -d "$repo_root/.specify" ]; do
  repo_root="$(dirname "$repo_root")"
done

exec "${REPO_ROOT:-$repo_root}/.specify/scripts/bash/update-agent-context.sh" droid
