# Design Artifact Golden Set

This directory is **spec-kit-plus design quality baseline library**, not ordinary
unit-test junk data.

Each fixture is a design-preview artifact expected to either:

- **pass** ready-level `design preview-lint`, or
- **fail** with specific diagnostic codes **and** recovery layers

## Layout

```text
valid/<name>/
  preview.html      # lint entrypoint
  manifest.json     # embedded manifest snapshot (readable source of truth)
  expected.json     # pass + empty diagnostics
  README.md

invalid/<name>/
  preview.html
  manifest.json
  expected.json     # fail + required diagnostic code/layer pairs
  README.md
```

## First batch

| Fixture | Kind | Governance intent |
| --- | --- | --- |
| `valid/industrial-erp` | pass | dense enterprise / multi-role workbench |
| `valid/consumer-app` | pass | airy consumer / marketing differentiation |
| `invalid/scaffold-leak` | fail semantic | scaffold baseline taste reasons |
| `invalid/metadata-cheat` | fail quality | metadata differs, visual fingerprint identical |
| `invalid/weak-divergence` | fail quality | dials only trivial single-axis steps |

## Regenerate

From repo root (after changing ready rules intentionally):

```bash
PYTHONPATH=src python scripts/generate-design-preview-golden-set.py
```

Then re-run:

```bash
pytest tests/test_design_artifact_golden_set.py -q
```

Do **not** “fix” a failing golden by weakening gates without updating the
governance contract and reviewing expected diagnostics.
