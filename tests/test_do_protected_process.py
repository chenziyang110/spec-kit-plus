"""Exercise the native protected-file boundary with synthetic external inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


RUNNER = Path(__file__).resolve().parents[1] / "scripts/shared/do_protected_process.py"
ENVIRONMENT = "SPECIFY_TEST_OFFICIAL_CONFIG"
SECRET = "synthetic-protected-configuration-content"


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _external_fingerprint(packet, paths):
    digest = hashlib.sha256()
    for name in sorted(packet["external_inputs"]):
        definition = packet["external_inputs"][name]
        location = str(paths[name].resolve())
        if os.name == "nt":
            location = location.lower()
        path_digest = hashlib.sha256(location.encode("utf-8")).hexdigest()
        row = [name, definition["environment"], definition["sha256"], path_digest]
        digest.update((json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii"))
    return digest.hexdigest()


def _fixture(tmp_path, *, modify_config=False, cwd="."):
    project = tmp_path / "project"
    project.mkdir()
    external = tmp_path / "protected" / "official.conf"
    external.parent.mkdir()
    external.write_text(SECRET, encoding="utf-8")
    execution_directory = project / cwd
    execution_directory.mkdir(parents=True, exist_ok=True)
    builder = execution_directory / "build.py"
    builder.write_text(
        "from pathlib import Path\nimport sys\n"
        "config = Path(sys.argv[1])\n"
        "print(str(config))\nprint(config.read_text())\n"
        "print(str(config), file=sys.stderr)\nprint(config.read_text(), file=sys.stderr)\n"
        "Path('artifact.bin').write_bytes(b'built')\n"
        + ("config.write_text('changed')\n" if modify_config else ""),
        encoding="utf-8",
    )
    packet = {
        "schema": "spec-kit-protected-process.v1", "cwd": cwd,
        "argv": [sys.executable, "build.py", "{{external:official_config}}"],
        "external_inputs": {"official_config": {"environment": ENVIRONMENT, "sha256": _digest(external)}},
        "source_files": {builder.relative_to(project).as_posix(): _digest(builder)},
        "attempt_id": "package-1", "definition_digest": "a" * 64, "source_fingerprint": "b" * 64,
    }
    packet["external_fingerprint"] = _external_fingerprint(packet, {"official_config": external})
    return project, external, builder, packet


def _invoke(project, external, packet, *, omit_environment=False, extra_environment=None):
    environment = os.environ.copy()
    environment.pop(ENVIRONMENT, None)
    if not omit_environment:
        environment[ENVIRONMENT] = str(external)
    environment.update(extra_environment or {})
    completed = subprocess.run(
        [sys.executable, str(RUNNER), "--input-json", "-"],
        input=json.dumps(packet), cwd=project, env=environment,
        text=True, capture_output=True, timeout=15, check=False,
    )
    assert completed.stderr == ""
    assert SECRET not in completed.stdout
    assert str(external) not in completed.stdout
    assert str(external.resolve()) not in completed.stdout
    for value in (extra_environment or {}).values():
        assert value not in completed.stdout
    return completed, json.loads(completed.stdout)


def test_protected_process_suppresses_child_output_and_never_copies_config(tmp_path):
    project, external, _, packet = _fixture(tmp_path, cwd="work/build")
    unused = external.parent / "unused.conf"
    unused.write_text("unused-protected-input", encoding="utf-8")
    unused_environment = "SPECIFY_TEST_UNUSED_CONFIG"
    packet["external_inputs"]["unused_config"] = {"environment": unused_environment, "sha256": _digest(unused)}
    packet["external_fingerprint"] = _external_fingerprint(packet, {"official_config": external, "unused_config": unused})
    completed, result = _invoke(project, external, packet, extra_environment={unused_environment: str(unused)})
    assert completed.returncode == 0
    assert result["outcome"] == "passed" and result["exit_code"] == 0
    assert result["argv"] == packet["argv"]
    assert result["used_bindings"] == [{"name": "official_config", "sha256": _digest(external)}]
    assert result["attempt_id"] == "package-1"
    assert result["definition_digest"] == packet["definition_digest"]
    assert result["source_fingerprint"] == packet["source_fingerprint"]
    assert result["external_fingerprint"] == packet["external_fingerprint"]
    assert external.read_text(encoding="utf-8") == SECRET
    assert (project / "work/build/artifact.bin").read_bytes() == b"built"
    assert {path.relative_to(project).as_posix() for path in project.rglob("*") if path.is_file()} == {
        "work/build/build.py", "work/build/artifact.bin",
    }
    verification = project / "work/build/verify.py"
    verification.write_text(
        "import os, sys\nfrom pathlib import Path\n"
        f"config = Path(os.environ[{ENVIRONMENT!r}])\n"
        "print(str(config))\nprint(config.read_text(), file=sys.stderr)\n",
        encoding="utf-8",
    )
    packet["argv"] = [sys.executable, "verify.py"]
    packet["source_files"]["work/build/verify.py"] = _digest(verification)
    completed, result = _invoke(project, external, packet, extra_environment={unused_environment: str(unused)})
    assert completed.returncode == 0
    assert result["outcome"] == "passed" and result["used_bindings"] == []


def test_protected_process_rejects_missing_or_internal_binding_without_paths(tmp_path):
    project, external, _, packet = _fixture(tmp_path)
    completed, result = _invoke(project, external, packet, omit_environment=True)
    assert completed.returncode == 2
    assert result["error"] == {"code": "external_input_missing", "binding": "official_config"}
    internal = project / "internal.conf"
    internal.write_text(SECRET, encoding="utf-8")
    completed, result = _invoke(project, internal, packet)
    assert completed.returncode == 2
    assert result["error"] == {"code": "external_input_inside_project", "binding": "official_config"}
    packet["cwd"] = "../outside"
    completed, result = _invoke(project, external, packet)
    assert completed.returncode == 2
    assert result["error"] == {"code": "cwd_invalid"}
    assert not (project / "artifact.bin").exists()


def test_protected_process_checks_external_and_source_hashes_before_launch(tmp_path):
    project, external, builder, packet = _fixture(tmp_path)
    original = external.read_bytes()
    external.write_bytes(b"different protected bytes")
    completed, result = _invoke(project, external, packet)
    assert completed.returncode == 2
    assert result["error"] == {"code": "external_input_hash_mismatch", "binding": "official_config"}
    external.write_bytes(original)
    alternate = external.parent / "alternate.conf"
    alternate.write_bytes(original)
    completed, result = _invoke(project, alternate, packet)
    assert completed.returncode == 2
    assert result["error"] == {"code": "external_fingerprint_mismatch"}
    builder.write_text("raise RuntimeError('must not execute changed source')\n", encoding="utf-8")
    completed, result = _invoke(project, external, packet)
    assert completed.returncode == 2
    assert result["error"] == {"code": "source_hash_mismatch"}
    assert not (project / "artifact.bin").exists()


def test_protected_process_detects_external_hash_change_after_execution(tmp_path):
    project, external, _, packet = _fixture(tmp_path, modify_config=True)
    completed, result = _invoke(project, external, packet)
    assert completed.returncode == 1
    assert result["outcome"] == "failed" and result["exit_code"] == 0
    assert result["error"] == {"code": "external_input_changed", "binding": "official_config"}
    assert (project / "artifact.bin").exists()
