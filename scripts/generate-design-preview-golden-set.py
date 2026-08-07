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
        lambda m: f"{m.group(1)}\n{rendered}\n  {m.group(2)}",
        content,
        count=1,
    )
    assert count == 1
    return updated


def _base_candidate() -> str:
    content = TEMPLATE.read_text(encoding="utf-8")
    content = content.replace(
        'data-preview-status="scaffold"',
        'data-preview-status="candidate"',
    )
    content = content.replace('"configured": false', '"configured": true')
    content = content.replace(
        '"status": "scaffold",\n    "approved_direction": null',
        '"status": "candidate",\n    "approved_direction": null',
    )
    content = re.sub(r"__[A-Z0-9_]+__", "Configured design content", content)
    return content


def _apply_taste(manifest: dict, taste: list[tuple[str, dict, str]]) -> None:
    for direction, (signature, dials, family) in zip(
        manifest["directions"], taste, strict=True
    ):
        direction["signature_element"] = signature
        direction["dials"] = dials
        direction["aesthetic_family"] = family


def _write_case(
    kind: str,
    name: str,
    content: str,
    expected: dict,
) -> None:
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
        f"# {name}\n\nGolden design-preview fixture ({kind}).\n",
        encoding="utf-8",
    )
    # verify
    diags = lint_design_preview_file(preview, level="ready")
    codes = [d.code for d in diags]
    if expected["result"] == "pass":
        assert not diags, f"{name} expected pass, got {codes}"
    else:
        want = {item["code"] for item in expected["diagnostics"]}
        got = set(codes)
        missing = want - got
        assert not missing, f"{name} missing codes {missing}; got {codes}"
    print(f"ok {kind}/{name}: {codes or 'pass'}")


def main() -> None:
    # --- valid: industrial-erp (dense, enterprise) ---
    content = _base_candidate()
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        [
            (
                "Status rail with critical-path operators",
                {
                    "variance": 3,
                    "motion": 2,
                    "density": 9,
                    "inference_reason": (
                        "Industrial ERP: operators need dense hierarchical scan "
                        "with minimal motion distraction"
                    ),
                },
                "workbench-precision",
            ),
            (
                "Command console with batch job focus",
                {
                    "variance": 5,
                    "motion": 4,
                    "density": 7,
                    "inference_reason": (
                        "Industrial ERP: balanced console density for multi-role "
                        "dispatch and exception handling"
                    ),
                },
                "data-dense-ops",
            ),
            (
                "Exception dossier with audit trail",
                {
                    "variance": 7,
                    "motion": 5,
                    "density": 5,
                    "inference_reason": (
                        "Industrial ERP: slightly more open layout for exception "
                        "investigation without losing operational density"
                    ),
                },
                "developer-tool-sharp",
            ),
        ],
    )
    # strengthen visual divergence on industrial (tweak density labels already differ)
    directions = manifest["directions"]
    directions[0]["typography"]["display"] = (
        '"IBM Plex Sans Condensed", "Segoe UI", sans-serif'
    )
    directions[1]["typography"]["display"] = (
        '"Bahnschrift", "Segoe UI", sans-serif'
    )
    directions[2]["typography"]["display"] = (
        '"Aptos Display", "Segoe UI", sans-serif'
    )
    content = _replace_preview_manifest(content, manifest)
    _write_case(
        "valid",
        "industrial-erp",
        content,
        {"result": "pass", "diagnostics": []},
    )

    # --- valid: consumer-app (airy, marketing) ---
    content = _base_candidate()
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        [
            (
                "Split hero with editorial media column",
                {
                    "variance": 8,
                    "motion": 7,
                    "density": 3,
                    "inference_reason": (
                        "Consumer app marketing: high layout variance and generous "
                        "whitespace for conversion-first storytelling"
                    ),
                },
                "marketing-editorial-asymmetric",
            ),
            (
                "Soft card stack with calm premium surfaces",
                {
                    "variance": 5,
                    "motion": 4,
                    "density": 5,
                    "inference_reason": (
                        "Consumer app product: calmer density for day-to-day "
                        "engagement with soft premium motion"
                    ),
                },
                "soft-premium-calm",
            ),
            (
                "Kinetic type ribbon with sparse sections",
                {
                    "variance": 9,
                    "motion": 9,
                    "density": 2,
                    "inference_reason": (
                        "Consumer brand moment: expressive motion and low density "
                        "to differentiate acquisition surfaces"
                    ),
                },
                "industrial-brutalist",
            ),
        ],
    )
    directions = manifest["directions"]
    directions[0]["geometry"]["radius_control"] = "999px"
    directions[0]["geometry"]["radius_surface"] = "4px"
    directions[1]["geometry"]["radius_control"] = "12px"
    directions[1]["geometry"]["radius_surface"] = "20px"
    directions[2]["geometry"]["radius_control"] = "0px"
    directions[2]["geometry"]["radius_surface"] = "0px"
    content = _replace_preview_manifest(content, manifest)
    _write_case(
        "valid",
        "consumer-app",
        content,
        {"result": "pass", "diagnostics": []},
    )

    # --- invalid: scaffold-leak ---
    content = _base_candidate()
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        [
            (
                "Configured signature A",
                {
                    "variance": 5,
                    "motion": 3,
                    "density": 7,
                    "inference_reason": "Scaffold baseline: balanced enterprise direction A",
                },
                "minimal-product-linear",
            ),
            (
                "Configured signature B",
                {
                    "variance": 7,
                    "motion": 5,
                    "density": 5,
                    "inference_reason": "Scaffold baseline: balanced enterprise direction B",
                },
                "developer-tool-sharp",
            ),
            (
                "Configured signature C",
                {
                    "variance": 8,
                    "motion": 7,
                    "density": 3,
                    "inference_reason": "Scaffold baseline: balanced enterprise direction C",
                },
                "marketing-editorial-asymmetric",
            ),
        ],
    )
    content = _replace_preview_manifest(content, manifest)
    _write_case(
        "invalid",
        "scaffold-leak",
        content,
        {
            "result": "fail",
            "diagnostics": [
                {"code": "preview-scaffold-taste-reason", "layer": "semantic"}
            ],
        },
    )

    # --- invalid: metadata-cheat (same visual fingerprint) ---
    content = _base_candidate()
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        [
            (
                "Precision enterprise language",
                {
                    "variance": 4,
                    "motion": 3,
                    "density": 7,
                    "inference_reason": "Project intake: metadata claims precision",
                },
                "precision",
            ),
            (
                "Futuristic enterprise language",
                {
                    "variance": 7,
                    "motion": 5,
                    "density": 5,
                    "inference_reason": "Project intake: metadata claims futuristic",
                },
                "futuristic",
            ),
            (
                "Editorial enterprise language",
                {
                    "variance": 8,
                    "motion": 7,
                    "density": 3,
                    "inference_reason": "Project intake: metadata claims editorial",
                },
                "editorial",
            ),
        ],
    )
    first = manifest["directions"][0]
    shared = {
        key: deepcopy(first[key])
        for key in (
            "typography",
            "geometry",
            "density",
            "elevation",
            "motion",
            "modes",
        )
    }
    for direction in manifest["directions"]:
        direction.update(deepcopy(shared))
    content = _replace_preview_manifest(content, manifest)
    _write_case(
        "invalid",
        "metadata-cheat",
        content,
        {
            "result": "fail",
            "diagnostics": [
                {
                    "code": "preview-undifferentiated-direction-visuals",
                    "layer": "quality",
                }
            ],
        },
    )

    # --- invalid: weak-divergence ---
    content = _base_candidate()
    manifest = _preview_manifest(content)
    _apply_taste(
        manifest,
        [
            (
                "Near twin A",
                {
                    "variance": 5,
                    "motion": 5,
                    "density": 5,
                    "inference_reason": "Project intake: weakly different A",
                },
                "family-a",
            ),
            (
                "Near twin B",
                {
                    "variance": 5,
                    "motion": 5,
                    "density": 6,
                    "inference_reason": "Project intake: weakly different B",
                },
                "family-b",
            ),
            (
                "Near twin C",
                {
                    "variance": 5,
                    "motion": 5,
                    "density": 7,
                    "inference_reason": "Project intake: weakly different C",
                },
                "family-c",
            ),
        ],
    )
    content = _replace_preview_manifest(content, manifest)
    _write_case(
        "invalid",
        "weak-divergence",
        content,
        {
            "result": "fail",
            "diagnostics": [
                {
                    "code": "preview-insufficient-direction-divergence",
                    "layer": "quality",
                }
            ],
        },
    )

    print("golden set written to", OUT)


if __name__ == "__main__":
    main()
