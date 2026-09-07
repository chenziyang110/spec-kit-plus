from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from tests.test_design_cli import _write_candidate_image_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLASSIC_DESIGN_REFERENCES = PROJECT_ROOT / "templates" / "command-references" / "design"
ADVANCED_DESIGN = PROJECT_ROOT / "templates" / "advanced-skills" / "spx-design"
runner = CliRunner()
TEST_IMAGE_PROMPT = (
    "# Image Generation Prompt\n\n"
    "Direction: direction-main\n\n"
    "Must preserve the declared boundaries.\n"
    "Must not exceed the declared scope.\n"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _image_source(path: Path) -> Path:
    source = path / "generated.png"
    source.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
            "0000000b4944415478da63fcff1f0002eb01f569769f570000000049454e44ae426082"
        )
    )
    return source


def _lowered_design_prompts() -> tuple[str, str]:
    classic = "\n".join(
        _read(path)
        for path in (
            CLASSIC_DESIGN_REFERENCES / "task-router.md",
            CLASSIC_DESIGN_REFERENCES / "image-generation-studio.md",
            CLASSIC_DESIGN_REFERENCES / "critique-loop.md",
        )
    ).lower()
    advanced = "\n".join(
        _read(path)
        for path in (
            ADVANCED_DESIGN / "SKILL.md",
            ADVANCED_DESIGN / "references" / "task-router.md",
            ADVANCED_DESIGN / "references" / "image-round.md",
            ADVANCED_DESIGN / "references" / "studio-loop.md",
        )
    ).lower()
    return classic, advanced


def test_design_prompt_cli_creates_runtime_owned_prompt_from_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, manifest, prompt, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9201",
        round_number="01",
    )
    prompt.unlink()
    prompt.with_name(prompt.name.removesuffix(".prompt.md") + ".generation.json").unlink()

    result = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=TEST_IMAGE_PROMPT,
    )

    assert result.exit_code == 0, result.output
    assert prompt.is_file()
    content = prompt.read_text(encoding="utf-8")
    assert "Image Generation Prompt" in content
    assert "direction-main" in content
    assert "Must preserve" in content
    assert "Must not" in content


def test_design_prompt_cli_binds_exact_stdin_content_create_only(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, manifest, prompt, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9210",
        round_number="10",
        prepare_prompt=False,
    )
    exact_prompt = (
        "# Exact ImageGen Edit Prompt\n\n"
        "Edit the attached live-product baseline only. Preserve the shell exactly.\n"
    )

    created = runner.invoke(
        app,
        [
            "design",
            "prompt",
            str(manifest),
            "--content",
            "-",
            "--format",
            "json",
        ],
        input=exact_prompt,
    )

    assert created.exit_code == 0, created.output
    created_payload = json.loads(created.stdout)
    assert created_payload["sha256"] == hashlib.sha256(
        exact_prompt.encode("utf-8")
    ).hexdigest()
    assert created_payload["receipt"]["content_authority"] == "agent-authored-exact"
    assert prompt.read_text(encoding="utf-8") == exact_prompt
    generation_path = prompt.with_name(
        prompt.name.removesuffix(".prompt.md") + ".generation.json"
    )
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    assert generation["content_authority"] == "agent-authored-exact"
    assert generation["prompt_sha256"] == hashlib.sha256(
        exact_prompt.encode("utf-8")
    ).hexdigest()

    retried = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=exact_prompt,
    )
    assert retried.exit_code == 0, retried.output

    replacement = exact_prompt.replace("only", "and redraw everything")
    rejected = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=replacement,
    )
    assert rejected.exit_code != 0
    assert "new numbered round" in rejected.output.lower()
    assert prompt.read_text(encoding="utf-8") == exact_prompt

    force_rejected = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-", "--force"],
        input=replacement,
    )
    assert force_rejected.exit_code != 0

    generation_path.unlink()
    partial_rejected = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=exact_prompt,
    )
    assert partial_rejected.exit_code != 0
    assert "partial" in partial_rejected.output.lower()


def test_design_prompt_cli_rejects_invalid_exact_content(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, manifest, _, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9211",
        round_number="11",
        prepare_prompt=False,
    )

    for content in (
        "   \n",
        "valid prefix\x00invalid suffix",
        "x" * (256 * 1024 + 1),
    ):
        result = runner.invoke(
            app,
            ["design", "prompt", str(manifest), "--content", "-"],
            input=content,
        )
        assert result.exit_code != 0


def test_design_prompt_cli_rejects_non_draft_and_round_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, manifest, _, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9212",
        round_number="12",
        prepare_prompt=False,
    )
    index_path = tmp_path / ".specify" / "design" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    record = next(item for item in index["changes"] if item["id"] == "UD-9212")
    record["status"] = "approved"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")

    immutable = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=TEST_IMAGE_PROMPT,
    )
    assert immutable.exit_code != 0
    assert "draft change workspace" in immutable.output.lower()

    record["status"] = "draft"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_payload["review"]["round"] = "13"
    manifest.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n"
    )
    wrong_round = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=TEST_IMAGE_PROMPT,
    )
    assert wrong_round.exit_code != 0
    assert "round-nn filename" in wrong_round.output.lower()


def test_design_prompt_rejects_unresolved_surface_posture(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, manifest, prompt, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9206",
        round_number="06",
        surface_posture=None,
        prepare_prompt=False,
    )
    assert not prompt.exists()

    result = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=TEST_IMAGE_PROMPT,
    )

    assert result.exit_code != 0
    assert "surface posture" in result.output.lower()


def test_design_prompt_inherit_existing_image_lane_requires_edit_baseline(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, manifest, prompt, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9202",
        round_number="02",
    )
    prompt.unlink()
    prompt.with_name(prompt.name.removesuffix(".prompt.md") + ".generation.json").unlink()
    baseline = tmp_path / "src" / "app" / "materials" / "current.png"
    baseline.parent.mkdir(parents=True)
    baseline.write_bytes(_image_source(tmp_path).read_bytes())
    design_path = (
        tmp_path
        / ".specify"
        / "design"
        / "changes"
        / "UD-9202"
        / "design-change.md"
    )
    design_text = design_path.read_text(encoding="utf-8").replace(
        "    mode: greenfield\n"
        "    scope_level: null\n"
        "    source_refs: []\n"
        "    protected_surfaces: []\n"
        "    allowed_style_delta_surfaces: []\n"
        "    authorization_source: null\n",
        "    mode: inherit-existing\n"
        "    scope_level: feature-partial\n"
        "    source_refs: [src/app/materials/page.tsx]\n"
        "    protected_surfaces: [global-shell, shared-components]\n"
        "    allowed_style_delta_surfaces: []\n"
        "    authorization_source: null\n",
        1,
    )
    design_path.write_text(design_text, encoding="utf-8")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["visual_collaboration"]["image_editing"] = "available"
    payload["input_images"] = [
        {
            "ref": "src/app/materials/current.png",
            "role": "edit-source",
            "surface_ids": ["global-shell", "shared-components"],
            "fidelity": "exact",
        }
    ]
    continuity = payload["handoff"]["source_continuity"]
    continuity["coverage"]["surface_ids"].extend(
        ["global-shell", "shared-components"]
    )
    continuity["surface_bindings"].extend(
        [
            {
                "id": "SC-SURFACE-901",
                "surface_id": surface,
                "source_refs": ["src/app/materials/current.png"],
                "discovery": "measured",
                "disposition": "preserve",
                "use_intent": "exact",
                "fidelity": "exact",
                "rationale": "The existing product shell is outside the editable feature surface.",
            }
            for surface in ("global-shell", "shared-components")
        ]
    )
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    inherited_prompt = (
        "# Image Generation Prompt\n\nOperation: edit\n\n"
        "Edit src/app/materials/current.png while preserving global-shell "
        "and shared-components exactly.\n"
    )
    result = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=inherited_prompt,
    )

    assert result.exit_code == 0, result.output
    content = prompt.read_text(encoding="utf-8").lower()
    assert "edit" in content
    assert "src/app/materials/current.png" in content
    assert "global-shell" in content
    assert "shared-components" in content


def test_inherit_existing_concept_receipt_requires_protected_surface_inspection(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    image, manifest, prompt, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9205",
        round_number="05",
    )
    baseline = tmp_path / "src" / "app" / "materials" / "current.png"
    baseline.parent.mkdir(parents=True)
    baseline.write_bytes(image.read_bytes())
    design_path = (
        tmp_path
        / ".specify"
        / "design"
        / "changes"
        / "UD-9205"
        / "design-change.md"
    )
    design_path.write_text(
        design_path.read_text(encoding="utf-8").replace(
            "    mode: greenfield\n"
            "    scope_level: null\n"
            "    source_refs: []\n"
            "    protected_surfaces: []\n"
            "    allowed_style_delta_surfaces: []\n"
            "    authorization_source: null\n",
            "    mode: inherit-existing\n"
            "    scope_level: feature-partial\n"
            "    source_refs: [src/app/materials/page.tsx]\n"
            "    protected_surfaces: [global-shell, shared-components]\n"
            "    allowed_style_delta_surfaces: []\n"
            "    authorization_source: null\n",
            1,
        ),
        encoding="utf-8",
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["visual_collaboration"]["image_editing"] = "available"
    payload["input_images"] = [
        {
            "ref": "src/app/materials/current.png",
            "role": "edit-source",
            "surface_ids": ["global-shell", "shared-components"],
            "fidelity": "exact",
        }
    ]
    continuity = payload["handoff"]["source_continuity"]
    continuity["coverage"]["surface_ids"].extend(
        ["global-shell", "shared-components"]
    )
    continuity["surface_bindings"].extend(
        [
            {
                "id": f"SC-SURFACE-90{index}",
                "surface_id": surface,
                "source_refs": ["src/app/materials/current.png"],
                "discovery": "measured",
                "disposition": "preserve",
                "use_intent": "exact",
                "fidelity": "exact",
                "rationale": "Protected live-product baseline.",
            }
            for index, surface in enumerate(
                ("global-shell", "shared-components"), start=1
            )
        ]
    )
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    prompt.unlink()
    prompt.with_name(prompt.name.removesuffix(".prompt.md") + ".generation.json").unlink()
    prepared = runner.invoke(
        app,
        ["design", "prompt", str(manifest), "--content", "-"],
        input=(
            "# Image Generation Prompt\n\nOperation: edit\n\n"
            "Edit src/app/materials/current.png while preserving global-shell "
            "and shared-components exactly.\n"
        ),
    )
    missing = runner.invoke(
        app,
        ["design", "preview-lint", str(image), "--level", "concept"],
    )
    review = {
        "verdict": "pass",
        "reviewer": "agent",
        "protected_surfaces": [
            {
                "surface_id": surface,
                "baseline_ref": "src/app/materials/current.png",
                "status": "preserved",
                "evidence": "Compared the saved pixels against the exact edit-source baseline.",
            }
            for surface in ("global-shell", "shared-components")
        ],
        "observed_differences": [
            {
                "surface_id": "web:orders/detail",
                "summary": "Updated only the bounded workbench content.",
                "authorized": True,
            }
        ],
    }
    inspected = runner.invoke(
        app,
        [
            "design",
            "preview-lint",
            str(image),
            "--level",
            "concept",
            "--inspection-json",
            json.dumps(review),
        ],
    )

    assert prepared.exit_code == 0, prepared.output
    assert missing.exit_code != 0
    assert "inspection-json" in missing.output
    assert inspected.exit_code == 0, inspected.output
    receipt = json.loads(image.with_suffix(".concept.json").read_text(encoding="utf-8"))
    assert receipt["visual_review"] == review


def test_design_import_change_round_requires_generation_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    created = runner.invoke(
        app,
        [
            "design",
            "change",
            "UD-9203",
            "--title",
            "Generation-bound import",
            "--scope",
            "web:materials/list",
            "--profiles",
            "web",
        ],
    )
    assert created.exit_code == 0, created.output

    result = runner.invoke(
        app,
        [
            "design",
            "import",
            str(_image_source(tmp_path)),
            "--change",
            "UD-9203",
            "--round",
            "1",
        ],
    )

    assert result.exit_code != 0
    assert "generation" in result.output.lower()


def test_concept_lint_writes_receipt_and_direction_confirm_rejects_prompt_drift(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    image, manifest, prompt, _, _ = _write_candidate_image_bundle(
        tmp_path,
        change_id="UD-9204",
        round_number="04",
    )

    linted = runner.invoke(
        app,
        ["design", "preview-lint", str(image), "--level", "concept", "--format", "json"],
    )
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\nDrift after lint.\n")
    confirmed = runner.invoke(
        app,
        [
            "design",
            "direction-confirm",
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
        ],
    )

    assert linted.exit_code == 0, linted.output
    receipt = image.with_suffix(".concept.json")
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == "spec-kit-design-concept-lint-receipt-v1"
    assert payload["prompt_sha256"] != hashlib.sha256(
        prompt.read_bytes()
    ).hexdigest()
    assert confirmed.exit_code != 0
    assert "concept receipt" in confirmed.output.lower()


def test_design_templates_separate_contract_action_from_surface_posture() -> None:
    for content in _lowered_design_prompts():
        assert "contract_action" in content
        assert "surface_posture" in content
        assert "contract_action" in content.split("surface_posture")[0]
        assert "create | refine | audit" in content
        assert "inherit-existing" in content

    generation_schema = json.loads(
        _read(PROJECT_ROOT / "templates" / "design-image-generation.schema.json")
    )
    assert "unresolved" not in generation_schema["properties"]["surface_posture"][
        "enum"
    ]


def test_design_templates_require_edit_baseline_before_inherit_existing_image_confirmation() -> None:
    for content in _lowered_design_prompts():
        assert "inherit-existing" in content
        assert "operation=edit" in content or "operation: edit" in content
        assert "edit-source" in content
        assert "global-shell" in content
        assert "shared-components" in content


def test_design_templates_persist_the_exact_professional_prompt_via_stdin() -> None:
    for content in _lowered_design_prompts():
        compact = " ".join(content.split())
        assert "design prompt" in compact
        assert "--content -" in compact
        assert "stdin" in compact
        assert "exact professional" in compact
        assert "create-only" in compact
        assert "already imported" in compact
        assert "exact prompt bytes are unavailable" in compact


def test_design_templates_request_direction_confirmation_only_after_lint_receipt() -> None:
    for content in _lowered_design_prompts():
        compact = " ".join(content.split())
        lint_index = compact.index("preview-lint")
        receipt_index = compact.index("concept receipt")
        confirm_index = compact.index("explicit direction confirmation")
        assert lint_index < receipt_index < confirm_index
        assert "lint pass alone must not create the direction" in compact
