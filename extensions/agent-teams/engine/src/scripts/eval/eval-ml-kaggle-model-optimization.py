from __future__ import annotations

import json
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "playground/ml_kaggle_demo/train.py"],
    check=False,
    capture_output=True,
    text=True,
)

if result.stdout:
    sys.stderr.write(result.stdout)
if result.stderr:
    sys.stderr.write(result.stderr)

if result.returncode != 0:
    print(json.dumps({"pass": False, "score": 0.0}))
    raise SystemExit(result.returncode)

metrics = json.loads(result.stdout)
auc = float(metrics["roc_auc"])

# Baseline should pass, but score_improvement should still reward better architectures.
passed = auc >= 0.90
print(json.dumps({"pass": passed, "score": auc}))
raise SystemExit(0 if passed else 1)
