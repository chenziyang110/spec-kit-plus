from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import design as design_module
from specify_cli import app
from specify_cli.design import (
    DesignLintError,
    approve_design_preview,
    design_preview_approval_path,
    design_preview_handoff_path,
    lint_design_preview_file,
    scaffold_design_preview,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_TEMPLATE = REPO_ROOT / "templates" / "design-preview-template.html"
runner = CliRunner()


def _preview_manifest(content: str) -> dict[str, object]:
    match = re.search(
        r'<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>(.*?)</script>',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match is not None
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


def _replace_preview_manifest(
    content: str,
    manifest: dict[str, object],
) -> str:
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


def _diversify_direction_taste(manifest: dict[str, object]) -> None:
    """Keep ready fixtures content-comparable but dial/signature divergent."""

    directions = manifest.get("directions")
    assert isinstance(directions, list)
    taste = (
        (
            "Configured signature A",
            {
                "variance": 5,
                "motion": 3,
                "density": 7,
                "inference_reason": "Project intake: dense workspace hierarchy for operators",
            },
            "minimal-product-linear",
        ),
        (
            "Configured signature B",
            {
                "variance": 7,
                "motion": 5,
                "density": 5,
                "inference_reason": "Project intake: balanced product language for mixed tasks",
            },
            "developer-tool-sharp",
        ),
        (
            "Configured signature C",
            {
                "variance": 8,
                "motion": 7,
                "density": 3,
                "inference_reason": "Project intake: expressive marketing lean for acquisition",
            },
            "marketing-editorial-asymmetric",
        ),
    )
    for direction, (signature, dials, family) in zip(directions, taste, strict=True):
        assert isinstance(direction, dict)
        direction["signature_element"] = signature
        direction["dials"] = dials
        direction["aesthetic_family"] = family


def _candidate_preview() -> str:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
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
    manifest = _preview_manifest(content)
    _diversify_direction_taste(manifest)
    return _replace_preview_manifest(content, manifest)


def _render_manifest() -> dict[str, object]:
    manifest = _preview_manifest(_candidate_preview())
    manifest["configured"] = False
    directions = manifest["directions"]
    assert isinstance(directions, list)
    direction_values = (
        ("direction-ledger", "Evidence Ledger", "A visible evidence trail"),
        ("direction-ribbon", "Command Ribbon", "A persistent command surface"),
        ("direction-dossier", "Decision Dossier", "A structured decision record"),
    )
    for direction, (direction_id, name, signature) in zip(
        directions,
        direction_values,
        strict=True,
    ):
        assert isinstance(direction, dict)
        direction["id"] = direction_id
        direction["name"] = name
        direction["signature_element"] = signature
    _diversify_direction_taste(manifest)
    return manifest


def test_design_preview_template_is_a_freeform_three_direction_board() -> None:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")

    assert lint_design_preview_file(PREVIEW_TEMPLATE) == []
    assert content.count("data-direction-id=") == 3
    assert 'data-design-preview-schema="spec-kit-design-preview-v1"' in content
    assert "freeform" in content.lower()
    assert 'data-preview-section="foundations"' not in content
    assert 'id="capability-specimen-grid"' not in content
    assert "renderCapabilityBoard" not in content
    assert "prefers-reduced-motion: reduce" in content
    assert "--motion-duration-fast" in content
    assert "--motion-easing-emphasized" in content
    assert 'data-active-direction="direction-a"' in content
    assert "dataset.activeDirection" in content
    assert 'id="design-preview-manifest"' in content
    assert '"modes": {' in content
    assert '"high-contrast": {' in content
    assert 'id="direction-a"' in content
    assert "location.hash" in content
    assert "hashchange" in content
    assert '"schema": "spec-kit-design-capability-model-v1"' in content
    assert "https://" not in content
    assert "http://" not in content
    assert "<script src=" not in content


def test_design_preview_ready_lint_rejects_unconfigured_scaffold() -> None:
    diagnostics = lint_design_preview_file(PREVIEW_TEMPLATE, level="ready")

    assert any(item.code == "preview-not-candidate" for item in diagnostics)
    assert any(item.code == "preview-unresolved-placeholder" for item in diagnostics)


def test_design_preview_ready_lint_accepts_configured_candidate(tmp_path: Path) -> None:
    preview = tmp_path / "round-01.html"
    preview.write_text(_candidate_preview(), encoding="utf-8")

    assert lint_design_preview_file(preview, level="ready") == []


def test_design_preview_ready_lint_rejects_undifferentiated_dials(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    shared = {
        "variance": 6,
        "motion": 6,
        "density": 6,
        "inference_reason": "intentionally identical dials",
    }
    for direction in directions:
        assert isinstance(direction, dict)
        direction["dials"] = dict(shared)
    preview = tmp_path / "same-dials.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-undifferentiated-direction-dials" for item in diagnostics
    )


def test_design_preview_ready_lint_rejects_duplicate_signatures(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    for direction in directions:
        assert isinstance(direction, dict)
        direction["signature_element"] = "Same signature everywhere"
    preview = tmp_path / "same-signatures.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-undifferentiated-direction-signatures"
        for item in diagnostics
    )


def test_design_preview_manifest_schema_keeps_taste_fields_optional_on_v1() -> None:
    schema = json.loads(
        (REPO_ROOT / "templates" / "design-preview-manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    direction = schema["$defs"]["direction"]
    assert "dials" not in direction["required"]
    assert "aesthetic_family" not in direction["required"]
    assert "dials" in direction["properties"]
    assert "aesthetic_family" in direction["properties"]
    dials = schema["$defs"]["directionDials"]
    assert dials["required"] == ["variance", "motion", "density", "inference_reason"]


def test_design_preview_legacy_v1_without_taste_fields_passes_structural(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    for direction in manifest["directions"]:
        assert isinstance(direction, dict)
        direction.pop("dials", None)
        direction.pop("aesthetic_family", None)
    preview = tmp_path / "legacy-v1.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    structural = lint_design_preview_file(preview, level="structural")
    ready = lint_design_preview_file(preview, level="ready")

    assert not any(item.code == "preview-manifest-schema-error" for item in structural)
    assert any(item.code == "preview-missing-direction-dials" for item in ready)


def test_design_preview_ready_lint_rejects_missing_or_null_dials(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    first = directions[0]
    second = directions[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    first.pop("dials", None)
    second["dials"] = {
        "variance": None,
        "motion": None,
        "density": None,
        "inference_reason": "project-specific but axes still null",
    }
    preview = tmp_path / "bad-dials.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")
    codes = {item.code for item in diagnostics}

    assert "preview-missing-direction-dials" in codes
    assert "preview-invalid-direction-dials" in codes
    assert "preview-manifest-schema-error" not in codes


def test_design_preview_structural_lint_allows_identical_dials(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    shared = {
        "variance": 5,
        "motion": 5,
        "density": 5,
        "inference_reason": "identical only matters at ready",
    }
    for direction in manifest["directions"]:
        assert isinstance(direction, dict)
        direction["dials"] = dict(shared)
    preview = tmp_path / "structural-same-dials.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="structural")

    assert not any(
        item.code == "preview-undifferentiated-direction-dials" for item in diagnostics
    )
    assert not any(
        item.code == "preview-insufficient-direction-divergence" for item in diagnostics
    )


def test_design_preview_ready_lint_requires_dial_inference_and_family(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    first = directions[0]
    assert isinstance(first, dict)
    first["dials"] = {
        "variance": 4,
        "motion": 4,
        "density": 4,
        "inference_reason": "   ",
    }
    first["aesthetic_family"] = ""
    preview = tmp_path / "missing-inference.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")
    codes = {item.code for item in diagnostics}

    assert "preview-missing-dial-inference" in codes
    assert "preview-missing-aesthetic-family" in codes
    assert "preview-manifest-schema-error" not in codes


def test_design_preview_ready_rejects_scaffold_baseline_taste_reasons(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    for index, direction in enumerate(directions):
        assert isinstance(direction, dict)
        dials = direction["dials"]
        assert isinstance(dials, dict)
        dials["inference_reason"] = f"Scaffold baseline: leftover template {index}"
    preview = tmp_path / "scaffold-reason.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-scaffold-taste-reason" for item in diagnostics)


def test_design_preview_ready_rejects_near_duplicate_dial_vectors(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    near = (
        {"variance": 5, "motion": 5, "density": 5, "inference_reason": "near A"},
        {"variance": 5, "motion": 5, "density": 6, "inference_reason": "near B"},
        {"variance": 5, "motion": 5, "density": 7, "inference_reason": "near C"},
    )
    for direction, dials in zip(manifest["directions"], near, strict=True):
        assert isinstance(direction, dict)
        direction["dials"] = dials
    preview = tmp_path / "near-dials.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-insufficient-direction-divergence" for item in diagnostics
    )


def test_design_preview_ready_rejects_punctuation_only_signature_variants(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    signatures = ("Progress rail", "Progress rail.", "Progress  rail")
    for direction, signature in zip(manifest["directions"], signatures, strict=True):
        assert isinstance(direction, dict)
        direction["signature_element"] = signature
    preview = tmp_path / "near-signatures.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-undifferentiated-direction-signatures"
        for item in diagnostics
    )


def test_design_preview_ready_rejects_identical_visual_payloads(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    first = directions[0]
    assert isinstance(first, dict)
    shared_visual = {
        key: first[key]
        for key in (
            "typography",
            "geometry",
            "density",
            "elevation",
            "motion",
            "modes",
        )
    }
    for direction in directions:
        assert isinstance(direction, dict)
        direction.update(shared_visual)
    preview = tmp_path / "same-visuals.html"
    preview.write_text(_replace_preview_manifest(content, manifest), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-undifferentiated-direction-visuals" for item in diagnostics
    )


def test_design_preview_scaffold_template_uses_unresolved_taste_placeholders() -> None:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    manifest = _preview_manifest(content)
    for direction in manifest["directions"]:
        assert isinstance(direction, dict)
        dials = direction["dials"]
        assert isinstance(dials, dict)
        assert dials["variance"] is None
        assert dials["motion"] is None
        assert dials["density"] is None
        assert "__" in str(dials["inference_reason"])
        assert "__" in str(direction["aesthetic_family"])

    ready = lint_design_preview_file(PREVIEW_TEMPLATE, level="ready")
    codes = {item.code for item in ready}
    assert "preview-unresolved-placeholder" in codes


def test_design_preview_lint_rejects_remote_runtime_dependency(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "remote.html"
    preview.write_text(
        _candidate_preview().replace(
            "</head>",
            '<script src="https://cdn.example.com/runtime.js"></script></head>',
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-remote-dependency" for item in diagnostics)


def test_design_preview_lint_requires_exactly_three_unique_directions(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "directions.html"
    preview.write_text(
        _candidate_preview().replace('data-direction-id="direction-c"', ""),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-direction-count" for item in diagnostics)


def test_design_preview_lint_requires_reduced_motion_fallback(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "motion.html"
    preview.write_text(
        _candidate_preview().replace(
            "prefers-reduced-motion: reduce",
            "prefers-reduced-motion: no-preference",
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-missing-reduced-motion" for item in diagnostics)


def test_design_preview_ready_lint_requires_a_style_scope_for_each_direction(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "direction-style-scope.html"
    # Remove every direction-c style scope so ready lint reports a missing scope.
    preview.write_text(
        _candidate_preview().replace(
            'body[data-active-direction="direction-c"]',
            'body[data-active-direction="direction-b"]',
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-missing-direction-style" for item in diagnostics)


def test_design_preview_ready_lint_requires_executable_density_scale(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    first_direction = directions[0]
    assert isinstance(first_direction, dict)
    density = first_direction["density"]
    assert isinstance(density, dict)
    density.pop("scale", None)
    preview = tmp_path / "missing-density-scale.html"
    preview.write_text(
        _replace_preview_manifest(content, manifest),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-invalid-density-system" for item in diagnostics)


def test_design_preview_ready_lint_maps_every_decision_to_an_owner(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    token_map = manifest["token_map"]
    assert isinstance(token_map, list)
    manifest["token_map"] = [
        entry
        for entry in token_map
        if isinstance(entry, dict) and entry.get("decision_id") != "DS-COLOR-001"
    ]
    preview = tmp_path / "unmapped-decision.html"
    preview.write_text(
        _replace_preview_manifest(content, manifest),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-unmapped-decision" for item in diagnostics)


def test_design_preview_ready_lint_requires_handoff_coverage_for_every_decision(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    handoff = manifest["handoff"]
    assert isinstance(handoff, dict)
    acceptance = handoff["visual_acceptance_matrix"]
    assert isinstance(acceptance, list)
    for entry in acceptance:
        assert isinstance(entry, dict)
        entry["decision_ids"] = [
            decision_id
            for decision_id in entry["decision_ids"]
            if decision_id != "DS-MOTION-001"
        ]
    preview = tmp_path / "missing-handoff-coverage.html"
    preview.write_text(
        _replace_preview_manifest(content, manifest),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-incomplete-handoff-decision-coverage"
        for item in diagnostics
    )


def test_design_preview_lint_rejects_unresolved_local_fragment(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "broken-fragment.html"
    preview.write_text(
        _candidate_preview().replace(
            "</body>",
            '<a href="#missing-section">Broken local link</a></body>',
            1,
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-unresolved-fragment" for item in diagnostics)


def test_scaffold_design_preview_copies_template_without_overwriting(
    tmp_path: Path,
) -> None:
    output = tmp_path / ".specify" / "design" / "previews" / "round-01.html"

    written = scaffold_design_preview(output, template_path=PREVIEW_TEMPLATE)

    assert written == output
    output_content = output.read_text(encoding="utf-8")
    assert 'data-review-round="1"' in output_content
    assert '"round": "1"' in output_content
    with pytest.raises(DesignLintError, match="already exists"):
        scaffold_design_preview(output, template_path=PREVIEW_TEMPLATE)


def test_scaffold_design_preview_manifest_extracts_the_canonical_schema(
    tmp_path: Path,
) -> None:
    output = tmp_path / ".specify" / "design" / "previews" / "round-07.manifest.json"

    written = design_module.scaffold_design_preview_manifest(
        output,
        template_path=PREVIEW_TEMPLATE,
    )

    assert written == output
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["schema"] == "spec-kit-design-preview-manifest-v1"
    assert manifest["configured"] is False
    assert manifest["review"] == {
        "round": "7",
        "status": "scaffold",
        "approved_direction": None,
    }
    assert len(manifest["directions"]) == 3
    with pytest.raises(DesignLintError, match="already exists"):
        design_module.scaffold_design_preview_manifest(
            output,
            template_path=PREVIEW_TEMPLATE,
        )


def test_design_capability_catalog_covers_visual_and_no_ui_routes() -> None:
    profiles = design_module.design_capability_profiles()
    profiles_by_id = {profile["id"]: profile for profile in profiles}

    assert set(profiles_by_id) == {
        "web",
        "mobile",
        "desktop",
        "cli",
        "tui",
        "content",
        "no-ui",
    }
    assert profiles_by_id["no-ui"]["preview_required"] is False
    assert profiles_by_id["no-ui"]["specimens"] == []
    for profile_id in {"web", "mobile", "desktop", "cli", "tui", "content"}:
        profile = profiles_by_id[profile_id]
        assert profile["preview_required"] is True
        assert len(profile["specimens"]) == 3
        assert profile["capability_ids"]
        assert profile["targets"]


def test_design_preview_manifest_projects_hybrid_capability_profiles(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "round-09.manifest.json"
    design_module.scaffold_design_preview_manifest(
        manifest_path,
        profile_ids=["mobile", "cli"],
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model = manifest["capability_model"]

    assert model["profile_ids"] == ["mobile", "cli"]
    assert [profile["id"] for profile in model["profiles"]] == ["mobile", "cli"]
    assert {specimen["profile_id"] for specimen in model["specimens"]} == {
        "mobile",
        "cli",
    }
    specimen_ids = [specimen["id"] for specimen in model["specimens"]]
    assert len(specimen_ids) == 6
    assert all(
        direction["specimen_ids"] == specimen_ids
        for direction in manifest["directions"]
    )
    targets = manifest["handoff"]["responsive_matrix"]
    assert {target["profile_id"] for target in targets} == {"mobile", "cli"}
    target_profiles = {target["id"]: target["profile_id"] for target in targets}
    specimens_by_profile = {
        profile_id: [
            specimen["id"]
            for specimen in model["specimens"]
            if specimen["profile_id"] == profile_id
        ]
        for profile_id in model["profile_ids"]
    }
    assert all(
        row["specimen_ids"]
        == specimens_by_profile[target_profiles[row["target_id"]]]
        for row in manifest["handoff"]["visual_acceptance_matrix"]
    )


def test_no_ui_profile_exits_before_preview_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "round-10.manifest.json"

    with pytest.raises(DesignLintError, match="design_system_status"):
        design_module.scaffold_design_preview_manifest(
            output,
            profile_ids=["no-ui"],
        )

    assert not output.exists()


def test_ready_lint_rejects_direction_and_acceptance_specimen_drift(
    tmp_path: Path,
) -> None:
    content = _candidate_preview()
    manifest = _preview_manifest(content)
    model = manifest["capability_model"]
    assert isinstance(model, dict)
    specimens = model["specimens"]
    assert isinstance(specimens, list)
    directions = manifest["directions"]
    assert isinstance(directions, list)
    assert isinstance(directions[0], dict)
    directions[0]["specimen_ids"] = [specimens[0]["id"]]
    handoff = manifest["handoff"]
    assert isinstance(handoff, dict)
    acceptance = handoff["visual_acceptance_matrix"]
    assert isinstance(acceptance, list)
    assert isinstance(acceptance[0], dict)
    acceptance[0]["specimen_ids"] = [specimens[0]["id"]]
    preview = tmp_path / "specimen-drift.html"
    preview.write_text(
        _replace_preview_manifest(content, manifest),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code == "preview-direction-specimen-mismatch" for item in diagnostics
    )
    assert any(
        item.code == "preview-acceptance-specimen-mismatch" for item in diagnostics
    )


def test_design_profiles_and_profiled_manifest_cli(tmp_path: Path) -> None:
    profiles_result = runner.invoke(app, ["design", "profiles", "--format", "json"])
    assert profiles_result.exit_code == 0
    catalog = json.loads(profiles_result.stdout)
    assert catalog["schema"] == "spec-kit-design-capability-profiles-v1"
    assert any(profile["id"] == "content" for profile in catalog["profiles"])

    output = tmp_path / "round-11.manifest.json"
    scaffold_result = runner.invoke(
        app,
        [
            "design",
            "preview-manifest",
            "--profiles",
            "tui,content",
            "--out",
            str(output),
        ],
    )
    assert scaffold_result.exit_code == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["capability_model"]["profile_ids"] == ["tui", "content"]


def test_design_preview_manifest_cli_writes_editable_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output = Path(".specify/design/previews/round-08.manifest.json")

    result = runner.invoke(
        app,
        ["design", "preview-manifest", "--out", str(output)],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["review"]["round"] == "8"


def test_render_design_preview_builds_ready_html_from_manifest(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "round-04.manifest.json"
    manifest_path.write_text(
        json.dumps(_render_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output = tmp_path / "round-04.html"

    written = design_module.render_design_preview(
        manifest_path,
        output,
        template_path=PREVIEW_TEMPLATE,
    )

    assert written == output
    content = output.read_text(encoding="utf-8")
    assert lint_design_preview_file(output, level="ready") == []
    assert 'data-preview-status="candidate"' in content
    assert 'data-review-round="4"' in content
    assert "freeform" in content.lower()
    assert 'id="capability-specimen-grid"' not in content
    for direction_id in (
        "direction-ledger",
        "direction-ribbon",
        "direction-dossier",
    ):
        assert f'data-direction-id="{direction_id}"' in content
        assert f'body[data-active-direction="{direction_id}"]' in content
    rendered_manifest = _preview_manifest(content)
    assert rendered_manifest["configured"] is True
    assert rendered_manifest["review"] == {
        "round": "4",
        "status": "candidate",
        "approved_direction": None,
    }


def test_design_preview_cli_renders_manifest_to_freeform_board(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    manifest_path = Path("round-02.manifest.json")
    manifest_path.write_text(
        json.dumps(_render_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output = Path(".specify/design/previews/round-02.html")

    result = runner.invoke(
        app,
        [
            "design",
            "preview",
            "--manifest",
            str(manifest_path),
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert lint_design_preview_file(output, level="ready") == []


def test_render_design_preview_escapes_embedded_script_terminators(
    tmp_path: Path,
) -> None:
    manifest = _render_manifest()
    project = manifest["project"]
    assert isinstance(project, dict)
    project["name"] = "Safe </script><script>window.bad = true</script> project"
    manifest_path = tmp_path / "round-05.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output = tmp_path / "round-05.html"

    design_module.render_design_preview(
        manifest_path,
        output,
        template_path=PREVIEW_TEMPLATE,
    )

    content = output.read_text(encoding="utf-8")
    assert "</script><script>window.bad" not in content
    assert r"\u003c/script\u003e" in content
    rendered_manifest = _preview_manifest(content)
    rendered_project = rendered_manifest["project"]
    assert isinstance(rendered_project, dict)
    assert rendered_project["name"] == project["name"]


def test_render_design_preview_never_overwrites_an_approved_round(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "round-06.manifest.json"
    manifest_path.write_text(
        json.dumps(_render_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output = tmp_path / "round-06.html"
    design_module.render_design_preview(
        manifest_path,
        output,
        template_path=PREVIEW_TEMPLATE,
    )
    approve_design_preview(output, direction_id="direction-ledger")

    with pytest.raises(DesignLintError, match="approved"):
        design_module.render_design_preview(
            manifest_path,
            output,
            force=True,
            template_path=PREVIEW_TEMPLATE,
        )
    with pytest.raises(DesignLintError, match="approved"):
        design_module.scaffold_design_preview_manifest(
            manifest_path,
            force=True,
            template_path=PREVIEW_TEMPLATE,
        )


def test_scaffold_design_preview_never_overwrites_an_approved_round(
    tmp_path: Path,
) -> None:
    output = tmp_path / ".specify" / "design" / "previews" / "round-01.html"
    output.parent.mkdir(parents=True)
    output.write_text(_candidate_preview(), encoding="utf-8")
    approve_design_preview(output, direction_id="direction-a")
    approved = output.read_text(encoding="utf-8")

    with pytest.raises(DesignLintError, match="approved"):
        scaffold_design_preview(
            output,
            force=True,
            template_path=PREVIEW_TEMPLATE,
        )

    assert output.read_text(encoding="utf-8") == approved


def test_approve_design_preview_freezes_direction_and_binds_sidecar(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "round-03.html"
    preview.write_text(_candidate_preview(), encoding="utf-8")

    payload = approve_design_preview(preview, direction_id="direction-b")
    content = preview.read_text(encoding="utf-8")
    approval_path = design_preview_approval_path(preview)
    handoff_path = design_preview_handoff_path(preview)

    assert payload["direction_id"] == "direction-b"
    assert payload["decision_ids"]
    assert payload["handoff_contract_ids"]
    assert payload["capability_profile_ids"] == ["web"]
    assert payload["specimen_ids"] == [
        "SP-WEB-WORKSPACE-001",
        "SP-WEB-CONTROLS-001",
        "SP-WEB-COLLECTION-001",
    ]
    assert payload["handoff_file"] == "round-03.handoff.json"
    assert 'data-preview-status="approved"' in content
    assert 'data-approved-direction="direction-b"' in content
    assert '"status": "approved"' in content
    assert '"approved_direction": "direction-b"' in content
    for direction_id in ("direction-a", "direction-b", "direction-c"):
        assert f'body[data-active-direction="{direction_id}"]' in content, (
            f"approval corrupted the {direction_id} style scope"
        )
    assert approval_path.is_file()
    assert handoff_path.is_file()
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert handoff["schema"] == "spec-kit-design-handoff-v1"
    assert handoff["direction"]["id"] == "direction-b"
    assert handoff["approval"]["preview_sha256"] == payload["html_sha256"]
    assert handoff["reproduction"]["contract_ids"] == payload["handoff_contract_ids"]
    assert handoff["reproduction"]["capability_model"]["profile_ids"] == ["web"]
    assert all(
        row["approved_targets"]
        for row in handoff["reproduction"]["visual_acceptance_matrix"]
    )
    assert lint_design_preview_file(preview, level="ready") == []

    preview.write_text(
        content.replace(
            "Freeform design review board",
            "Freeform design review board (edited)",
        ),
        encoding="utf-8",
    )
    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-stale-approval-sidecar" for item in diagnostics)


def test_approved_preview_rejects_a_tampered_handoff(tmp_path: Path) -> None:
    preview = tmp_path / "round-09.html"
    preview.write_text(_candidate_preview(), encoding="utf-8")
    approve_design_preview(preview, direction_id="direction-a")
    handoff_path = design_preview_handoff_path(preview)
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["direction"]["signature_element"] = "Reinterpreted after approval"
    handoff_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(
        item.code in {"preview-stale-handoff-binding", "preview-stale-handoff-sidecar"}
        for item in diagnostics
    )


def test_design_preview_approve_cli_writes_immutable_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    preview = Path(".specify/design/previews/round-02.html")
    preview.parent.mkdir(parents=True)
    preview.write_text(_candidate_preview(), encoding="utf-8")

    result = runner.invoke(
        app,
        ["design", "approve", str(preview), "--direction", "direction-c", "--format", "json"],
    )

    assert result.exit_code == 0
    assert design_preview_approval_path(preview).is_file()
    assert '"direction_id": "direction-c"' in result.output


def test_design_preview_cli_scaffolds_and_lints_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output = Path(".specify/design/previews/round-01.html")

    scaffold_result = runner.invoke(app, ["design", "preview", "--out", str(output)])

    assert scaffold_result.exit_code == 0
    assert output.exists()
    output.write_text(_candidate_preview(), encoding="utf-8")

    lint_result = runner.invoke(
        app,
        ["design", "preview-lint", str(output), "--level", "ready"],
    )

    assert lint_result.exit_code == 0
    assert "valid at ready level" in lint_result.output


def test_design_preview_asset_is_packaged_and_installed_by_shared_template_copy() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"templates/design-preview-template.html" = '
        '"specify_cli/core_pack/templates/design-preview-template.html"'
    ) in pyproject
    assert '"templates/design-preview-manifest.schema.json"' in pyproject
    assert '"templates/design-handoff-schema.json"' in pyproject
    assert '"templates/design-capability-profiles.json"' in pyproject
    assert 'packages = ["src/specify_cli"]' in pyproject
    assert '"src/specify_cli/design_preview_source" =' not in pyproject
    assert (REPO_ROOT / "src" / "specify_cli" / "design_preview_source").is_dir()
    assert PREVIEW_TEMPLATE.exists()


def test_jinja_preview_source_matches_generated_compatibility_artifact() -> None:
    source, rendered = design_module._load_design_preview_template(None)

    assert source.name == "template.html.j2"
    assert source.stat().st_size < 1_000
    assert rendered == PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    assert "{% include" not in rendered
    assert "freeform" in rendered.lower()
    assert "capability-specimen-grid" not in rendered


def test_design_workflows_require_question_driven_three_option_iteration() -> None:
    classic = (
        REPO_ROOT / "templates" / "command-partials" / "design" / "shell.md"
    ).read_text(encoding="utf-8")
    advanced = (
        REPO_ROOT / "templates" / "advanced-skills" / "spx-design" / "SKILL.md"
    ).read_text(encoding="utf-8")
    combined = f"{classic}\n{advanced}".lower()

    assert "one high-impact design question at a time" in combined
    assert "exactly three" in combined
    assert "freeform" in combined
    assert "round-" in combined
    assert "until the user approves" in combined
    assert "do not overwrite" in combined
    assert "approved_visual_ref" in combined
    assert "motion" in combined
    assert "prefers-reduced-motion" in combined
    assert "feature-level `ui-target.html`" in combined
    assert "author creative" in combined or "hand-edit" in combined
    for workflow in (classic.lower(), advanced.lower()):
        assert "round-nn.manifest.json" in workflow
        assert "design preview-manifest" in workflow
        assert "design preview --manifest" in workflow
