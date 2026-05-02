from pathlib import Path
import re


HIGH_RISK_TEMPLATE_FILES = [
    Path("templates/commands/specify.md"),
    Path("templates/commands/plan.md"),
    Path("templates/commands/tasks.md"),
    Path("templates/commands/implement.md"),
    Path("templates/commands/analyze.md"),
    Path("templates/commands/quick.md"),
    Path("templates/commands/debug.md"),
    Path("templates/commands/deep-research.md"),
    Path("templates/commands/clarify.md"),
    Path("templates/commands/checklist.md"),
    Path("templates/commands/constitution.md"),
    Path("templates/commands/map-scan.md"),
    Path("templates/commands/map-build.md"),
    Path("templates/commands/test.md"),
    Path("templates/commands/test-scan.md"),
    Path("templates/commands/test-build.md"),
    Path("templates/command-partials/common/learning-layer.md"),
    Path("templates/command-partials/test-scan/shell.md"),
]


def test_high_risk_templates_do_not_use_bare_runtime_specify_calls():
    forbidden = re.compile(r"`?specify (hook|learning|result|testing inventory)\b")
    offenders = []

    for path in HIGH_RISK_TEMPLATE_FILES:
        content = path.read_text(encoding="utf-8")
        if forbidden.search(content):
            offenders.append(path.as_posix())

    assert offenders == []
