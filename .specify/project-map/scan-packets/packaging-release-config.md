# MapScanPacket: packaging-release-config

- lane_id: packaging-release-config
- mode: read_only
- scope: packaging metadata, force-included assets, CI workflows, devcontainer, extension/preset catalogs, release scripts.
- ledger_row_ids: L001, L006, L015

## required_reads

- `pyproject.toml`
- `uv.lock`
- `.github/workflows/**`
- `.github/workflows/scripts/**`
- `.github/dependabot.yml`
- `.github/CODEOWNERS`
- `.devcontainer/devcontainer.json`
- `.devcontainer/post-create.sh`
- `extensions/catalog*.json`
- `extensions/*GUIDE*.md`
- `presets/catalog*.json`
- `presets/README.md`
- `presets/PUBLISHING.md`
- `scripts/sync-ecc-to-codex.sh`
- `scripts/powershell/sync-ecc-to-codex.ps1`

## excluded_paths

- `dist/**`
- `.tmp-dist/**`

## required_questions

- Which assets are packaged into the wheel?
- Which CI/release surfaces validate Python, docs, packaging, or security?
- How do extension and preset catalogs fit into product boundaries?
- Which devcontainer/setup files affect local development?

## expected_outputs

- Packaging and release facts with force-included asset paths.
- CI/devcontainer and catalog ownership facts.
- Verification entry points for packaging/config changes.

## atlas_targets

- `.specify/project-map/root/STRUCTURE.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/root/TESTING.md`

## forbidden_actions

- Do not create release artifacts.
- Do not run publishing commands.

## result_handoff_path

`.specify/project-map/worker-results/packaging-release-config.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/test_packaging_assets.py tests/test_extensions.py tests/test_presets.py -q`
- `uv build`

## blocked_conditions

- `pyproject.toml` or CI/release files cannot be read.
