import ast
from pathlib import Path
import subprocess


def test_cli_run_command_capture_uses_explicit_utf8(monkeypatch):
    import specify_cli as cli_module

    seen: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    output = cli_module.run_command(["git", "status"], capture=True)

    assert output == "ok"
    assert seen["text"] is True
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"


def test_default_verification_runner_uses_explicit_utf8(monkeypatch):
    from specify_cli import verification

    seen: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="pass\n", stderr="")

    monkeypatch.setattr(verification.subprocess, "run", fake_run)

    code, output = verification.default_verification_runner("echo pass")

    assert code == 0
    assert output == "pass"
    assert seen["text"] is True
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"


def test_project_map_git_head_commit_uses_explicit_utf8(monkeypatch, tmp_path):
    from specify_cli import project_map_status

    seen: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="abc123\n", stderr="")

    monkeypatch.setattr(project_map_status.subprocess, "run", fake_run)

    commit = project_map_status.git_head_commit(tmp_path)

    assert commit == "abc123"
    assert seen["text"] is True
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"


def test_debug_utils_run_command_uses_explicit_utf8(monkeypatch):
    from specify_cli.debug import utils

    seen: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="stdout\n", stderr="stderr\n")

    monkeypatch.setattr(utils.subprocess, "run", fake_run)

    output = utils.run_command("git status")

    assert "stdout" in output
    assert "stderr" in output
    assert seen["text"] is True
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"


def test_debug_context_get_recent_git_changes_uses_explicit_utf8(monkeypatch, tmp_path):
    from specify_cli.debug.context import ContextLoader

    seen: dict[str, object] = {}

    def fake_check_output(*args, **kwargs):
        seen.update(kwargs)
        return "a.py\nb.py\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    files = ContextLoader(root_dir=Path(tmp_path)).get_recent_git_changes(limit=2)

    assert files == ["a.py", "b.py"]
    assert seen["text"] is True
    assert seen["encoding"] == "utf-8"
    assert seen["errors"] == "replace"


def test_source_subprocess_text_calls_use_explicit_utf8():
    project_root = Path(__file__).resolve().parents[1]
    source_root = project_root / "src" / "specify_cli"
    violations: list[str] = []

    for py_file in source_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in {"run", "check_output"}:
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "subprocess":
                continue

            keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            text_kw = keywords.get("text")
            if not isinstance(text_kw, ast.Constant) or text_kw.value is not True:
                continue

            encoding_kw = keywords.get("encoding")
            errors_kw = keywords.get("errors")
            if not (
                isinstance(encoding_kw, ast.Constant)
                and encoding_kw.value == "utf-8"
                and isinstance(errors_kw, ast.Constant)
                and errors_kw.value == "replace"
            ):
                violations.append(f"{py_file.relative_to(project_root)}:{node.lineno}")

    assert violations == []
