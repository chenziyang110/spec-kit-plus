"""Behavioral checks for archive validation, using explicitly synthetic wheels.

These are verifier tests, not a real specify-cli wheel installation. The separate
CI probe runs actual init/upgrade/repair in a wheel-only virtual environment.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tomllib
import warnings
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/workflow-quality/verify_e2e_wheel.py"
SPEC = importlib.util.spec_from_file_location("e2e_wheel_verifier", SCRIPT)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
PROBE = ROOT / "tests/e2e_samples/wheel_install_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("wheel_install_probe", PROBE)
probe = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(probe)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "synthetic source with spaces"
    files = set(verifier.ASSET_FILES)
    files.update(f"scripts/shared/{name}" for name in verifier.HELPERS)
    files.update(f"{directory}/nested/fixture.md" for directory in verifier.ASSET_TREES)
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"SYNTHETIC SOURCE {name}\n".encode())
    return root


def record_for(assets):
    rows = []
    for name, data in assets.items():
        value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        rows.append([name, "sha256=" + value, str(len(data))])
    return rows


def wheel_for(tmp_path, assets, record=None, extra=None):
    wheel = tmp_path / "synthetic.whl"
    stream = io.StringIO(newline="")
    csv.writer(stream).writerows(record_for(assets) if record is None else record)
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in assets.items():
            archive.writestr(name, data)
        archive.writestr("specify_cli-0.0.0.dist-info/RECORD", stream.getvalue())
        if extra:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                for name, data in extra:
                    # ZipInfo normalizes backslashes on Windows and truncates
                    # NULs. Preserve the deliberately malformed archive name
                    # so the reader, not the fixture writer, must reject it.
                    info = zipfile.ZipInfo(name)
                    info.filename = name
                    archive.writestr(info, data)
    return wheel


def test_valid_archive_binds_every_source_asset_and_record(source, tmp_path):
    assets = verifier.source_assets(source)
    wheel = wheel_for(tmp_path, assets)
    report = verifier.verify_wheel(wheel, source)
    assert report["claim"] == "wheel_e2e_assets_verified"
    assert report["asset_count"] == len(assets)
    assert {row["path"] for row in report["assets"]} == set(assets)
    assert report["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert "not installation" in report["qualification"]


@pytest.mark.parametrize("helper", verifier.HELPERS)
def test_each_missing_helper_is_a_packaging_failure(source, tmp_path, helper):
    assets = verifier.source_assets(source)
    del assets[f"specify_cli/core_pack/scripts/shared/{helper}"]
    with pytest.raises(verifier.WheelError, match="missing wheel asset"):
        verifier.verify_wheel(wheel_for(tmp_path, assets), source)


@pytest.mark.parametrize("source_path", [
    "src/specify_cli/specify_runtime.py",
    "src/specify_cli/execution/packet_validator.py",
    "tools/specify-runtime/e2e_workflow.go",
    "tools/specify-runtime/e2e_contract.go",
    "tools/specify-runtime/e2e_views.go",
])
@pytest.mark.parametrize("mutation", ["missing", "stale"])
def test_runtime_owner_and_compatibility_bridge_are_required(source, tmp_path, source_path, mutation):
    assets = verifier.source_assets(source)
    target = verifier.ASSET_FILES[source_path]
    if mutation == "missing":
        del assets[target]
    else:
        assets[target] = b"X" * len(assets[target])
    # A self-consistent RECORD cannot hide a stale or missing runtime owner.
    with pytest.raises(verifier.WheelError, match="missing wheel asset|bytes mismatch"):
        verifier.verify_wheel(wheel_for(tmp_path, assets), source)


@pytest.mark.parametrize("source_path", [
    "tools/specify-runtime/e2e_workflow.go",
    "tools/specify-runtime/e2e_contract.go",
    "tools/specify-runtime/e2e_views.go",
])
def test_deleted_runtime_owner_cannot_shrink_packaging_scope(source, tmp_path, source_path):
    wheel = wheel_for(tmp_path, verifier.source_assets(source))
    (source / source_path).unlink()
    with pytest.raises(verifier.WheelError, match="missing/escaping source"):
        verifier.verify_wheel(wheel, source)


@pytest.mark.parametrize("kind", ["size", "same-size"])
def test_changed_wheel_bytes_fail_even_with_consistent_record(source, tmp_path, kind):
    assets = verifier.source_assets(source)
    name = next(iter(assets))
    assets[name] = b"changed" if kind == "size" else b"X" * len(assets[name])
    with pytest.raises(verifier.WheelError, match="mismatch"):
        verifier.verify_wheel(wheel_for(tmp_path, assets), source)


@pytest.mark.parametrize("mutation", ["hash", "size", "missing", "duplicate", "malformed"])
def test_record_cannot_lie_about_assets(source, tmp_path, mutation):
    assets = verifier.source_assets(source)
    rows = record_for(assets)
    if mutation == "hash":
        rows[0][1] = "sha256=incorrect"
    elif mutation == "size":
        rows[0][2] = "0"
    elif mutation == "missing":
        rows.pop(0)
    elif mutation == "duplicate":
        rows.append(deepcopy(rows[0]))
    else:
        rows[0] = rows[0][:2]
    with pytest.raises(verifier.WheelError, match="RECORD"):
        verifier.verify_wheel(wheel_for(tmp_path, assets, rows), source)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\b", "a//b", "./same", "a\x00b"])
def test_unsafe_archive_members_rejected_without_extraction(source, tmp_path, name):
    assets = verifier.source_assets(source)
    wheel = wheel_for(tmp_path, assets, extra=[(name, b"not extracted")])
    with pytest.raises(verifier.WheelError, match="noncanonical ZIP"):
        verifier.verify_wheel(wheel, source)
    assert not (tmp_path.parent / "escape").exists()


def test_duplicate_member_rejected(source, tmp_path):
    assets = verifier.source_assets(source)
    name = next(iter(assets))
    with pytest.raises(verifier.WheelError, match="duplicate ZIP"):
        verifier.verify_wheel(wheel_for(tmp_path, assets, extra=[(name, assets[name])]), source)


def test_extra_record_rejected(source, tmp_path):
    with pytest.raises(verifier.WheelError, match="exactly one RECORD"):
        verifier.verify_wheel(wheel_for(tmp_path, verifier.source_assets(source),
                                       extra=[("other.dist-info/RECORD", b"")]), source)


def test_source_deletion_cannot_shrink_denominator(source, tmp_path):
    assets = verifier.source_assets(source)
    wheel = wheel_for(tmp_path, assets)
    (source / "templates/commands/e2e.md").unlink()
    with pytest.raises(verifier.WheelError, match="missing/escaping source"):
        verifier.verify_wheel(wheel, source)


def test_missing_source_tree_is_not_vacuous_success(source):
    import shutil
    shutil.rmtree(source / "templates/command-partials")
    with pytest.raises(verifier.WheelError, match="missing source tree"):
        verifier.source_assets(source)


def test_nested_references_are_included_and_caches_ignored(source):
    cache = source / "templates/advanced-skills/spx-e2e/__pycache__/unused.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"cache")
    assets = verifier.source_assets(source)
    assert any("/nested/fixture.md" in name for name in assets)
    assert not any("__pycache__" in name for name in assets)


OMITTED_NATIVE_PATHS = (
    "adapter-registry-cover.out", "tool-bridge-cover.out",
    ".tmp/00/build-output", ".tmp-go/test/output", ".tmp-gotmp-release-final/TestForeground/001/linked worktree/.git",
    ".tmp-gotmp-release-final/TestForeground/001/linked worktree/ordinary-file.go",
    ".gocache/cache-object", "bin/specify-runtime", ".git/config", ".hg/store/data", ".svn/entries", ".bzr/branch/format",
)
RETAINED_NATIVE_PATHS = (
    "go.mod", "go.sum", "e2e_views.go", "context/context.go", "internal/testdata/.hidden-input",
    "internal/testdata/.gitignore", "internal/testdata/.tmp-fixture/input.json", "internal/testdata/bin/expected.json",
    ".source-contract", ".tmp-contract-file", "temporary-source.go",
)


def native_boundary_files(source):
    for name in OMITTED_NATIVE_PATHS + RETAINED_NATIVE_PATHS:
        path = source / "tools/specify-runtime" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("SYNTHETIC " + name + "\n").encode())


def test_known_native_temporary_roots_are_pruned_without_shrinking_hidden_sources(source, tmp_path, monkeypatch):
    native_boundary_files(source)
    original_walk = verifier.os.walk

    def checked_walk(directory):
        for parent, directories, files in original_walk(directory):
            relative = Path(parent).relative_to(source)
            # The excluded trees must not even be visited (e.g. linked worktrees
            # and concurrently written Go cache entries are outside inventory).
            assert not verifier.excluded_source(PurePosixPath(relative.as_posix()), directory=True)
            yield parent, directories, files

    monkeypatch.setattr(verifier.os, "walk", checked_walk)
    assets = verifier.source_assets(source)
    prefix = "specify_cli/core_pack/tools/specify-runtime/"
    assert all(prefix + name not in assets for name in OMITTED_NATIVE_PATHS)
    assert all(prefix + name in assets for name in RETAINED_NATIVE_PATHS)
    wheel = wheel_for(tmp_path, assets)
    assert verifier.verify_wheel(wheel, source)["claim"] == "wheel_e2e_assets_verified"
    # Mutating ignored data cannot silently authorize dropping a real source.
    target = prefix + "internal/testdata/.hidden-input"
    del assets[target]
    with pytest.raises(verifier.WheelError, match="missing wheel asset"):
        verifier.verify_wheel(wheel_for(tmp_path, assets), source)


@pytest.mark.parametrize("mutation", ["missing", "corrupt"])
def test_ordinary_hidden_native_testdata_remains_a_required_asset(source, tmp_path, mutation):
    native_boundary_files(source)
    assets = verifier.source_assets(source)
    target = "specify_cli/core_pack/tools/specify-runtime/internal/testdata/.hidden-input"
    if mutation == "missing":
        del assets[target]
    else:
        assets[target] = b"X" * len(assets[target])
    with pytest.raises(verifier.WheelError, match="missing wheel asset|bytes mismatch"):
        verifier.verify_wheel(wheel_for(tmp_path, assets), source)


@pytest.mark.parametrize("name", OMITTED_NATIVE_PATHS)
def test_old_wheel_cannot_keep_excluded_native_contents(source, tmp_path, name):
    assets = verifier.source_assets(source)
    # An old or manually assembled wheel must not pass merely because its
    # temporary contents were removed from the expected source inventory.
    assets["specify_cli/core_pack/tools/specify-runtime/" + name] = b"local-only"
    with pytest.raises(verifier.WheelError, match="excluded local/VCS asset"):
        verifier.verify_wheel(wheel_for(tmp_path, assets), source)


def test_actual_hatch_wheel_excludes_only_known_native_roots_and_vcs(source, tmp_path):
    # Hatch is the declared build backend, not an application dependency. Run
    # this packaging check with `uv run --with hatchling pytest ...`.
    pytest.importorskip("hatchling", reason="real wheel exclusion check requires the declared Hatch build backend")
    from hatchling.builders.wheel import WheelBuilder
    native_boundary_files(source)
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel_config = deepcopy(config["tool"]["hatch"]["build"]["targets"]["wheel"])
    # The tiny synthetic project supplies only the actual owner trees used by
    # this verifier. Its force-inclusion keys/destinations and excludes come
    # unchanged from the repository's real distribution contract.
    wheel_config["force-include"] = {name: target for name, target in wheel_config["force-include"].items() if (source / name).exists()}
    synthetic_config = {"project": {"name": "specify-cli", "version": "0.0.0"},
        "tool": {"hatch": {"build": {"targets": {"wheel": wheel_config}}}}}
    destination = tmp_path / "actual-hatch-wheel"
    destination.mkdir()
    builder = WheelBuilder(str(source), config=synthetic_config)
    built = list(builder.build(directory=str(destination)))
    assert len(built) == 1
    wheel = Path(built[0])
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    prefix = "specify_cli/core_pack/tools/specify-runtime/"
    assert not [name for name in OMITTED_NATIVE_PATHS if prefix + name in names]
    assert not [name for name in RETAINED_NATIVE_PATHS if prefix + name not in names]
    assert all("specify_cli/core_pack/scripts/shared/" + helper in names for helper in verifier.HELPERS)
    assert verifier.verify_wheel(wheel, source)["claim"] == "wheel_e2e_assets_verified"


@pytest.mark.parametrize("optimized", [False, True])
def test_cli_preserves_failure_and_does_not_write(source, tmp_path, optimized):
    assets = verifier.source_assets(source)
    wheel = wheel_for(tmp_path, assets)
    command = [sys.executable] + (["-O"] if optimized else []) + [str(SCRIPT), "--wheel", str(wheel), "--source-root", str(source)]
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = subprocess.run(command, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["asset_count"] == len(assets)
    assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    del assets[next(iter(assets))]
    wheel_for(tmp_path, assets)
    result = subprocess.run(command, text=True, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert not result.stdout
    assert json.loads(result.stderr)["claim"] == "invalid"


def test_probe_rejects_existing_evidence_directory(tmp_path):
    output = tmp_path / "evidence"
    output.mkdir()
    sentinel = output / "previous.json"
    sentinel.write_text("retain previous run")
    result = subprocess.run([sys.executable, "-I", str(PROBE), "--wheel", "missing.whl", "--runtime", "missing",
                             "--output", str(output), "--expected-revision", "fixture"], capture_output=True, timeout=20)
    assert result.returncode != 0
    assert sentinel.read_text() == "retain previous run"
    assert not (output / "result.json").exists()


def test_probe_missing_runtime_is_failure_not_success(tmp_path):
    output = tmp_path / "new-evidence"
    result = subprocess.run([sys.executable, "-I", str(PROBE), "--wheel", "missing.whl", "--runtime", "missing",
                             "--output", str(output), "--expected-revision", "fixture"], capture_output=True, timeout=20)
    assert result.returncode == 1
    assert json.loads((output / "error.json").read_text())["claim"] == "failed"
    assert not (output / "result.json").exists()


def test_child_environment_does_not_reuse_source_pythonpath_or_runtime_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/unrelated/source")
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", "/unrelated/binary")
    monkeypatch.setenv("SPECIFY_RUNTIME_CACHE_DIR", "/unrelated/cache")
    runtime = tmp_path / "test-runtime"
    env = probe.clean_environment(tmp_path, runtime)
    assert "PYTHONPATH" not in env
    assert env["SPECIFY_RUNTIME_BIN"] == str(runtime)
    assert env["SPECIFY_RUNTIME_CACHE_DIR"] == str(tmp_path / "runtime-cache")
    assert env["SPECIFY_PROJECT_LAUNCHER_STATE_DIR"] == str(tmp_path / "launcher-state")


def test_probe_isolation_gate_precedes_package_import(tmp_path):
    with pytest.raises(RuntimeError, match="with -I"):
        probe.installed_assets(tmp_path / "missing.whl")
