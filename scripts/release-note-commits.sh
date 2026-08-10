#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <revision-or-range>" >&2
  exit 1
fi

range="$1"

git log --no-merges --pretty=format:%s "$range" | awk '
  {
    subject = $0
    normalized = tolower(subject)
  }
  normalized ~ /^chore: release v?[0-9]+\.[0-9]+\.[0-9]+/ { next }
  normalized ~ /^chore: bump version to [0-9]+\.[0-9]+\.[0-9]+([-.][0-9a-z.-]+)?$/ { next }
  normalized ~ /^chore: begin [0-9]+\.[0-9]+\.[0-9]+\.dev0 development$/ { next }
  { print "- " subject }
'
