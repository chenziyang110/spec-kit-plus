"""Automated team dispatch hook for Codex projects.

This script is intended to be called by the Codex CLI 'notify' hook after
each agent turn. It scans for ready parallel batches and dispatches them
to the team runtime.
"""

import sys
import json
from pathlib import Path

from specify_cli.codex_team.auto_dispatch import (
    run_notify_hook,
)

def main():
    # Codex CLI passes the payload as the last argument
    if len(sys.argv) < 2:
        return

    try:
        payload = json.loads(sys.argv[-1])
    except (json.JSONDecodeError, IndexError):
        return

    run_notify_hook(payload)

if __name__ == "__main__":
    main()
