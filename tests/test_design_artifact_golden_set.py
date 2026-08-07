"""Design Artifact Golden Set — governance regression for design previews.

These fixtures lock the stable ready-level contract:

- valid artifacts must pass
- invalid artifacts must fail with expected diagnostic codes and layers

They are not free-form unit tests; they are the quality baseline library for
AI design artifact governance (#81–#83).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.design import lint_design_preview_file


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "design-preview"
READY_LEVEL = "ready"


@dataclass(frozen=True)
class DesignPreviewFixture:
    path: Path
    kind: str
    name: str
    preview: Path
    expected: dict[str, object]

    @property
    def id(self) -> str:
        return f"{self.kind}/{self.name}"


def discover_design_preview_fixtures() -> list[DesignPreviewFixture]:
    fixtures: list[DesignPreviewFixture] = []
    if not FIXTURE_ROOT.is_dir():
        return fixtures
    for kind in ("valid", "invalid"):
        kind_root = FIXTURE_ROOT / kind
        if not kind_root.is_dir():
            continue
        for case_dir in sorted(p for p in kind_root.iterdir() if p.is_dir()):
            preview = case_dir / "preview.html"
            expected_path = case_dir / "expected.json"
            if not preview.is_file() or not expected_path.is_file():
                continue
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            fixtures.append(
                DesignPreviewFixture(
                    path=case_dir,
                    kind=kind,
                    name=case_dir.name,
                    preview=preview,
                    expected=expected,
                )
            )
    return fixtures


def _assert_expected_diagnostics(
    diagnostics: list[object],
    expected_items: list[dict[str, object]],
) -> None:
    """Require each expected code/layer pair to appear at least once."""

    got = {
        (
            str(getattr(item, "code", "")),
            str(getattr(item, "layer", "") or ""),
        )
        for item in diagnostics
    }
    missing: list[str] = []
    for expected in expected_items:
        code = str(expected.get("code") or "")
        layer = str(expected.get("layer") or "")
        if (code, layer) not in got:
            missing.append(f"{code}/{layer}")
    assert not missing, (
        "missing expected diagnostics "
        f"{missing}; got={sorted(got)}"
    )


@pytest.mark.parametrize(
    "fixture",
    discover_design_preview_fixtures(),
    ids=lambda item: item.id if isinstance(item, DesignPreviewFixture) else str(item),
)
def test_design_preview_golden_fixture(fixture: DesignPreviewFixture) -> None:
    expected_result = str(fixture.expected.get("result") or "").strip().lower()
    assert expected_result in {"pass", "fail"}
    assert fixture.preview.is_file()
    assert (fixture.path / "manifest.json").is_file()

    diagnostics = lint_design_preview_file(fixture.preview, level=READY_LEVEL)
    codes = [getattr(item, "code", "") for item in diagnostics]

    if expected_result == "pass":
        assert diagnostics == [], (
            f"{fixture.id} must pass ready lint; got codes={codes}"
        )
        assert fixture.expected.get("diagnostics") in ([], None)
        return

    expected_diagnostics = fixture.expected.get("diagnostics")
    assert isinstance(expected_diagnostics, list) and expected_diagnostics, (
        f"{fixture.id} invalid fixtures must declare expected diagnostics"
    )
    assert diagnostics, f"{fixture.id} must fail ready lint"
    _assert_expected_diagnostics(diagnostics, expected_diagnostics)


def test_design_preview_golden_set_contains_first_batch() -> None:
    discovered = {item.id for item in discover_design_preview_fixtures()}
    required = {
        "valid/industrial-erp",
        "valid/consumer-app",
        "invalid/scaffold-leak",
        "invalid/metadata-cheat",
        "invalid/weak-divergence",
    }
    assert required <= discovered, f"missing golden fixtures: {required - discovered}"


def test_design_preview_golden_set_has_regenerator_script() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "generate-design-preview-golden-set.py"
    )
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "industrial-erp" in text
    assert "metadata-cheat" in text
    assert "weak-divergence" in text
