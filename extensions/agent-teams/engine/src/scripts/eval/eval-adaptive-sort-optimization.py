from __future__ import annotations

import json
import subprocess
import sys

result = subprocess.run(
    [sys.executable, 'playground/adaptive_sort_demo/sort_benchmark.py'],
    check=False,
    capture_output=True,
    text=True,
)
if result.stdout:
    sys.stderr.write(result.stdout)
if result.stderr:
    sys.stderr.write(result.stderr)
if result.returncode != 0:
    print(json.dumps({'pass': False, 'score': 0.0}))
    raise SystemExit(result.returncode)

payload = json.loads(result.stdout)
total_cost = float(payload['total_cost'])
score = 10000.0 / total_cost
print(json.dumps({'pass': total_cost > 0, 'score': score}))
