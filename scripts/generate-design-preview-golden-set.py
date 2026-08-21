"""Generate Design Artifact Golden Set fixtures under tests/fixtures/design-preview/."""
from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from specify_cli.design import lint_design_preview_file  # noqa: E402

TEMPLATE = REPO / "templates" / "design-preview-template.html"
OUT = REPO / "tests" / "fixtures" / "design-preview"


def _preview_manifest(content: str) -> dict:
    match = re.search(
        r'<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>(.*?)</script>',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match is not None
    return json.loads(match.group(1))


def _replace_preview_manifest(content: str, manifest: dict) -> str:
    pattern = re.compile(
        r'(<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>).*?(</script>)',
        re.DOTALL | re.IGNORECASE,
    )
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2)
    updated, count = pattern.subn(
        lambda match: f"{match.group(1)}\n{rendered}\n  {match.group(2)}",
        content,
        count=1,
    )
    assert count == 1
    return updated


def _base_candidate() -> str:
    content = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        'data-preview-status="scaffold"': 'data-preview-status="candidate"',
        'data-prototype-status="seed"': 'data-prototype-status="authored"',
        '"configured": false': '"configured": true',
        '"status": "scaffold",\n    "approved_direction": null': (
            '"status": "candidate",\n    "approved_direction": null'
        ),
        "freeform-seed": "authored-concept",
        "Unfinished prototype seed": "Project-specific current concept",
        "Replace this seed with the complete project-specific concept before review.": (
            "Review representative content, states, and actions in this workspace."
        ),
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    return re.sub(r"__[A-Z0-9_]+__", "Configured design content", content)


def _apply_taste(
    manifest: dict,
    *,
    signature: str,
    dials: dict,
    family: str,
) -> dict:
    directions = manifest["directions"]
    assert len(directions) == 1
    direction = directions[0]
    direction["signature_element"] = signature
    direction["dials"] = dials
    direction["aesthetic_family"] = family
    return direction


def _write_case(kind: str, name: str, content: str, expected: dict) -> None:
    root = OUT / kind / name
    root.mkdir(parents=True, exist_ok=True)
    preview = root / "preview.html"
    preview.write_text(content, encoding="utf-8")
    manifest = _preview_manifest(content)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "expected.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {name}\n\nGolden single-concept design-preview fixture ({kind}).\n",
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")
    codes = [diagnostic.code for diagnostic in diagnostics]
    if expected["result"] == "pass":
        assert not diagnostics, f"{name} expected pass, got {codes}"
    else:
        wanted = {item["code"] for item in expected["diagnostics"]}
        missing = wanted - set(codes)
        assert not missing, f"{name} missing codes {missing}; got {codes}"
    print(f"ok {kind}/{name}: {codes or 'pass'}")


def main() -> None:
    content = _base_candidate()
    manifest = _preview_manifest(content)
    direction = _apply_taste(
        manifest,
        signature="Status rail with critical-path operators",
        dials={
            "variance": 3,
            "motion": 2,
            "density": 9,
            "inference_reason": (
                "Industrial ERP operators need dense hierarchy with minimal motion"
            ),
        },
        family="workbench-precision",
    )
    direction["typography"]["display"] = (
        '"IBM Plex Sans Condensed", "Segoe UI", sans-serif'
    )
    _write_case(
        "valid",
        "industrial-erp",
        _replace_preview_manifest(content, manifest),
        {"result": "pass", "diagnostics": []},
    )

    content = _base_candidate()
    manifest = _preview_manifest(content)
    direction = _apply_taste(
        manifest,
        signature="Editorial progress ribbon",
        dials={
            "variance": 8,
            "motion": 7,
            "density": 3,
            "inference_reason": (
                "Consumer app needs generous space and expressive, purposeful feedback"
            ),
        },
        family="marketing-editorial-asymmetric",
    )
    direction["geometry"]["radius_control"] = "999px"
    direction["geometry"]["radius_surface"] = "20px"
    _write_case(
        "valid",
        "consumer-app",
        _replace_preview_manifest(content, manifest),
        {"result": "pass", "diagnostics": []},
    )

    content = _base_candidate()
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        signature="Configured signature",
        dials={
            "variance": 5,
            "motion": 3,
            "density": 7,
            "inference_reason": "Scaffold baseline: generic enterprise styling",
        },
        family="minimal-product-linear",
    )
    _write_case(
        "invalid",
        "scaffold-leak",
        _replace_preview_manifest(content, manifest),
        {
            "result": "fail",
            "diagnostics": [
                {"code": "preview-scaffold-taste-reason", "layer": "semantic"}
            ],
        },
    )

    content = _base_candidate().replace(
        'data-prototype-status="authored"',
        'data-prototype-status="seed"',
    )
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        signature="Metadata claims completion",
        dials={
            "variance": 5,
            "motion": 4,
            "density": 6,
            "inference_reason": "Project intake: balanced operational workspace",
        },
        family="workbench-precision",
    )
    _write_case(
        "invalid",
        "metadata-cheat",
        _replace_preview_manifest(content, manifest),
        {
            "result": "fail",
            "diagnostics": [
                {"code": "preview-unfinished-prototype", "layer": "quality"}
            ],
        },
    )

    content = _base_candidate()
    manifest = _preview_manifest(content)
    direction = _apply_taste(
        manifest,
        signature="Current concept",
        dials={
            "variance": 5,
            "motion": 4,
            "density": 6,
            "inference_reason": "Project intake: current concept baseline",
        },
        family="minimal-product-linear",
    )
    extra = deepcopy(direction)
    extra["id"] = "direction-extra"
    manifest["directions"].append(extra)
    _write_case(
        "invalid",
        "weak-divergence",
        _replace_preview_manifest(content, manifest),
        {
            "result": "fail",
            "diagnostics": [
                {"code": "preview-manifest-direction-count", "layer": "structural"}
            ],
        },
    )

    print("golden set written to", OUT)


if __name__ == "__main__":
    main()
