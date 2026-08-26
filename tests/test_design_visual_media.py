from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.design import (
    approve_design_image,
    design_preview_approval_path,
    design_preview_handoff_path,
    lint_design_image_bundle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_TEMPLATE = REPO_ROOT / "templates" / "design-preview-template.html"
CLASSIC_UI_SKILL = (
    REPO_ROOT / "templates" / "passive-skills" / "spec-kit-ui-design"
)
ADVANCED_DESIGN_SKILL = REPO_ROOT / "templates" / "advanced-skills" / "spx-design"
runner = CliRunner()

IMAGE_BYTES_BY_SUFFIX = {
    ".png": base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII="
    ),
    ".jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00design-round",
    ".jpeg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00design-round",
    ".webp": b"RIFF\x04\x00\x00\x00WEBP",
}


def _candidate_manifest() -> dict[str, object]:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    match = re.search(
        r'<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>(.*?)</script>',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match is not None
    manifest = json.loads(match.group(1))
    manifest["configured"] = True
    manifest["review"]["status"] = "candidate"
    manifest["project"].update(
        {
            "name": "Atlas Operations",
            "short_name": "Atlas",
            "subject": "incident response workspace",
            "audience": "operations leads",
            "single_job": "triage and recover a production incident",
            "brief": "A dense incident response workspace for operations leads.",
        }
    )
    direction = manifest["directions"][0]
    direction["signature_element"] = "Persistent recovery rail"
    direction["dials"] = {
        "variance": 5,
        "motion": 3,
        "density": 7,
        "inference_reason": "Dense operator workflow",
    }
    direction["aesthetic_family"] = "minimal-product-linear"
    manifest["handoff"]["source_continuity"] = {
        "schema": "spec-kit-ui-source-continuity-v1",
        "applicability": "not-applicable",
        "mode": "none",
        "reason": "This fixture exercises greenfield image review behavior.",
        "coverage": {"surface_ids": [], "interaction_ids": [], "component_ids": []},
        "authority_refs": [],
        "surface_bindings": [],
        "action_bindings": [],
        "asset_bindings": [],
        "unresolved_gaps": [],
    }
    rendered = json.dumps(manifest)
    rendered = re.sub(r"__[A-Z0-9_]+__", "Configured design content", rendered)
    return json.loads(rendered)


def _write_image_candidate(
    tmp_path: Path,
    *,
    suffix: str = ".png",
) -> tuple[Path, Path, Path]:
    image = tmp_path / f"round-01{suffix}"
    image.write_bytes(IMAGE_BYTES_BY_SUFFIX[suffix])
    manifest = tmp_path / "round-01.manifest.json"
    manifest.write_text(
        json.dumps(_candidate_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    prompt = tmp_path / "round-01.prompt.md"
    prompt.write_text(
        "# Image generation prompt\n\n"
        "One composite UI review board for Atlas Operations. Preserve the persistent "
        "recovery rail; show the primary incident workspace and labeled state specimens.\n",
        encoding="utf-8",
    )
    return image, manifest, prompt


def test_design_workflows_route_visual_medium_from_live_capabilities() -> None:
    classic = (
        REPO_ROOT / "templates" / "command-partials" / "design" / "shell.md"
    ).read_text(encoding="utf-8")
    advanced = (ADVANCED_DESIGN_SKILL / "SKILL.md").read_text(encoding="utf-8")
    brief = (REPO_ROOT / "templates" / "design-brief-template.md").read_text(
        encoding="utf-8"
    )
    combined = f"{classic}\n{advanced}\n{brief}".lower()

    for capability in ("image_generation", "image_inspection", "image_editing"):
        assert capability in combined
    assert "live capability" in combined
    assert "do not hard-code" in combined
    assert "image-primary" in combined
    assert "html-primary" in combined
    assert "agent-and-user" in combined
    assert "inspection_owner: user" in combined
    assert "no visual-quality claim" in combined
    assert "one current concept" in combined


def test_image_and_html_rounds_use_separate_professional_prompt_contracts() -> None:
    classic_image = CLASSIC_UI_SKILL / "references" / "image-generation-studio.md"
    classic_html = CLASSIC_UI_SKILL / "references" / "html-prototype-studio.md"
    advanced_image = ADVANCED_DESIGN_SKILL / "references" / "image-round.md"
    advanced_html = ADVANCED_DESIGN_SKILL / "references" / "html-round.md"

    for path in (classic_image, classic_html, advanced_image, advanced_html):
        assert path.is_file(), path

    image_text = f"{classic_image.read_text(encoding='utf-8')}\n{advanced_image.read_text(encoding='utf-8')}".lower()
    html_text = f"{classic_html.read_text(encoding='utf-8')}\n{advanced_html.read_text(encoding='utf-8')}".lower()

    for term in (
        "subject",
        "context",
        "style",
        "composition",
        "aspect ratio",
        "exact text",
        "invariants",
        "generate",
        "edit",
    ):
        assert term in image_text
    for term in (
        "semantic html",
        "dom",
        "css",
        "responsive",
        "interaction",
        "browser capture",
    ):
        assert term in html_text
    assert "do not reuse the html authoring prompt" in image_text
    assert "do not send this html authoring contract to an image model" in html_text


def test_approve_design_image_freezes_image_manifest_prompt_and_capabilities(
    tmp_path: Path,
) -> None:
    image, manifest, prompt = _write_image_candidate(tmp_path)

    payload = approve_design_image(
        image,
        manifest_path=manifest,
        prompt_path=prompt,
        direction_id="direction-main",
        image_inspection="available",
        image_editing="available",
    )

    approved_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    handoff = json.loads(
        design_preview_handoff_path(image).read_text(encoding="utf-8")
    )
    assert payload["visual_medium"] == "image"
    assert payload["image_sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert payload["prompt_sha256"] == hashlib.sha256(prompt.read_bytes()).hexdigest()
    assert payload["inspection_owner"] == "agent-and-user"
    assert approved_manifest["review"]["status"] == "approved"
    assert approved_manifest["review"]["approved_direction"] == "direction-main"
    assert approved_manifest["visual_collaboration"] == {
        "primary_medium": "image-primary",
        "image_generation": "available",
        "image_inspection": "available",
        "image_editing": "available",
        "inspection_owner": "agent-and-user",
        "prompt_strategy": "image-generation",
    }
    assert handoff["approval"]["visual_medium"] == "image"
    assert handoff["approval"]["preview_sha256"] == payload["image_sha256"]
    assert handoff["approval"]["prompt_sha256"] == payload["prompt_sha256"]
    assert lint_design_image_bundle(image) == []

    image.write_bytes(image.read_bytes() + b"tampered")
    diagnostics = lint_design_image_bundle(image)
    assert any(item.code == "image-stale-approval-sidecar" for item in diagnostics)


def test_image_generation_without_vision_records_user_owned_inspection(
    tmp_path: Path,
) -> None:
    image, manifest, prompt = _write_image_candidate(tmp_path)

    payload = approve_design_image(
        image,
        manifest_path=manifest,
        prompt_path=prompt,
        direction_id="direction-main",
        image_inspection="unavailable",
        image_editing="unavailable",
    )

    assert payload["inspection_owner"] == "user"
    assert payload["image_inspection"] == "unavailable"
    assert payload["image_editing"] == "unavailable"
    assert lint_design_image_bundle(image) == []


@pytest.mark.parametrize("suffix", [".jpg", ".jpeg", ".webp"])
def test_image_approval_supports_each_declared_raster_format(
    tmp_path: Path,
    suffix: str,
) -> None:
    image, manifest, prompt = _write_image_candidate(tmp_path, suffix=suffix)

    payload = approve_design_image(
        image,
        manifest_path=manifest,
        prompt_path=prompt,
        direction_id="direction-main",
        image_inspection="available",
        image_editing="unavailable",
    )

    assert payload["preview_file"] == image.name
    assert payload["image_sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert lint_design_image_bundle(image) == []


def test_design_approve_cli_dispatches_image_rounds(tmp_path: Path) -> None:
    image, manifest, prompt = _write_image_candidate(tmp_path)

    result = runner.invoke(
        app,
        [
            "design",
            "approve",
            str(image),
            "--direction",
            "direction-main",
            "--manifest",
            str(manifest),
            "--prompt",
            str(prompt),
            "--image-inspection",
            "available",
            "--image-editing",
            "unavailable",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert design_preview_approval_path(image).is_file()
    assert '"visual_medium": "image"' in result.output


@pytest.mark.parametrize("suffix", [".svg", ".txt", ".html"])
def test_image_approval_rejects_non_raster_artifacts(tmp_path: Path, suffix: str) -> None:
    image, manifest, prompt = _write_image_candidate(tmp_path)
    invalid = image.with_suffix(suffix)
    invalid.write_bytes(image.read_bytes())

    with pytest.raises(Exception, match="PNG|JPEG|WEBP|image"):
        approve_design_image(
            invalid,
            manifest_path=manifest,
            prompt_path=prompt,
            direction_id="direction-main",
            image_inspection="available",
            image_editing="unavailable",
        )
