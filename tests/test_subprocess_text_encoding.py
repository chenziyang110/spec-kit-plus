import ast
import json
import os
from pathlib import Path
import subprocess
import sys


class _FakeTextStream:
    def __init__(self, encoding: str | None):
        self.encoding = encoding


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


def test_source_subprocess_text_calls_use_explicit_utf8_error_policy():
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
                and errors_kw.value in {"replace", "strict"}
            ):
                violations.append(f"{py_file.relative_to(project_root)}:{node.lineno}")

    assert violations == []


def test_render_json_for_stdout_preserves_unicode_on_utf8_stream():
    from specify_cli.cli_output import render_json_for_stdout

    rendered = render_json_for_stdout({"summary": "demo ✅"}, stream=_FakeTextStream("utf-8"))

    assert "✅" in rendered
    assert "\\u2705" not in rendered


def test_render_json_for_stdout_falls_back_to_ascii_for_gbk_stream():
    from specify_cli.cli_output import render_json_for_stdout

    rendered = render_json_for_stdout({"summary": "demo ✅"}, stream=_FakeTextStream("gbk"))

    assert "✅" not in rendered
    assert "\\u2705" in rendered


def test_non_utf8_subprocess_json_is_ascii_safe_for_cjk_workspace(tmp_path):
    workspace = tmp_path / "PI项目研究"
    workspace.mkdir()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "gbk"
    script = (
        "from pathlib import Path; "
        "from specify_cli.cli_output import print_json; "
        "print_json({'workspace_path': str(Path.cwd())})"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        env=env,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("gbk", errors="replace")
    raw = result.stdout.decode("ascii")
    assert json.loads(raw)["workspace_path"] == str(workspace)
    assert "项目研究" not in raw
    assert "\\u9879" in raw
