from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.design import (
    DesignLintError,
    _design_impact_classes,
    _quick_confirmation_digest,
    adopt_design_change,
    approve_design_preview,
    diff_design_changes,
    export_design_system,
    import_design_reference,
    impact_design_adoption,
    lint_design_file,
    parse_design_markdown,
    register_design_change,
    resolve_design_changes,
    scaffold_design_change,
    scaffold_design_iteration,
)


runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_TEMPLATE = REPO_ROOT / "templates" / "design-preview-template.html"


VALID_DESIGN = """---
design_system:
  schema: spec-kit-design-v1
  name: test-system
  version: 1
  status: approved
  approval:
    status: approved
    direction: direction-a
    review_round: 1
    source_refs:
      - src/app/page.tsx
    visual_refs:
      - .specify/design/previews/round-01.html#direction-a
    preview_sha256: PREVIEW_SHA256
    manifest_sha256: MANIFEST_SHA256
    handoff_ref: .specify/design/previews/round-01.handoff.json
    handoff_sha256: HANDOFF_SHA256
    decision_ids:
      - DS-COLOR-001
      - DS-TYPE-001
      - DS-SPACE-001
      - DS-COMP-001
      - DS-MOTION-001
      - DS-RESP-001
      - DS-CONTENT-001
    handoff_contract_ids: HANDOFF_CONTRACT_IDS
    capability_profile_ids:
      - web
    specimen_ids:
      - SP-WEB-WORKSPACE-001
      - SP-WEB-CONTROLS-001
      - SP-WEB-COLLECTION-001
  product_context:
    subject: account settings
    audience: account owners
    single_job: update preferences
  direction_contract:
    visual_thesis: compact hierarchy
    content_thesis: real preference values
    interaction_thesis: immediate local feedback
    signature_element: section progress rail
    safe_system_choices:
      - semantic tokens
    creative_risks:
      - compact density
  platforms:
    - web
  capability_profiles:
    - web
  specimens:
    - SP-WEB-WORKSPACE-001
    - SP-WEB-CONTROLS-001
    - SP-WEB-COLLECTION-001
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: app background
      text.primary:
        value: "#111827"
        usage: primary text
    spacing:
      scale.4:
        value: "16px"
        usage: default gap
    radius:
      control:
        value: "6px"
        usage: controls
    typography:
      body.family:
        value: "system-ui"
        usage: body text
    motion:
      duration.fast:
        value: "140ms"
        usage: direct control feedback
      easing.standard:
        value: "cubic-bezier(.2, .8, .2, 1)"
        usage: continuous state change
    elevation:
      surface:
        value: "0 8px 24px rgb(0 0 0 / 12%)"
        usage: raised surfaces
    sizing:
      control.default:
        value: "44px"
        usage: controls
    layout:
      content.max:
        value: "1200px"
        usage: application content
  color_modes:
    light:
      canvas: "{color.surface.canvas}"
  components:
    button:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - loading
      token_refs:
        background: "{color.surface.canvas}"
        text: "{color.text.primary}"
      decision_refs:
        - DS-COMP-001
        - DS-COLOR-001
  responsive:
    breakpoints:
      compact: "680px"
    adaptations:
      - collapse navigation before content
  content:
    voice_rules:
      - concise and actionable
    real_content_sources:
      - src/app/page.tsx
    imagery_rules: []
  decisions:
    - id: DS-COLOR-001
      kind: color
      statement: use accessible semantic color pairs
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: contrast report and visual capture
    - id: DS-TYPE-001
      kind: typography
      statement: preserve compact readable hierarchy
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: resolved font and visual capture
    - id: DS-SPACE-001
      kind: spacing
      statement: preserve the spacing rhythm
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: computed tokens and visual capture
    - id: DS-COMP-001
      kind: component
      statement: preserve component anatomy and states
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: state matrix and structure snapshot
    - id: DS-MOTION-001
      kind: motion
      statement: preserve purposeful feedback and reduced motion
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: runtime capture
    - id: DS-RESP-001
      kind: responsive
      statement: preserve hierarchy across target widths
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: viewport matrix
    - id: DS-CONTENT-001
      kind: content
      statement: preserve representative content density
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: content evidence and visual capture
  verification:
    required_viewports:
      - "390"
      - "1024"
    required_states:
      - default
      - loading
      - error
    visual_tolerance: no unapproved structural drift; rendering variance documented
    accepted_deviations: []
  accessibility:
    contrast_intent: WCAG AA
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
    touch_target: 44px minimum
    forced_colors: supported
---

# Design

## Product Feel

Purposeful and compact.

## Design Direction

Direction A is approved.

## Visual And Interaction Signature

Use the section progress rail.

## Foundations

Use the approved semantic tokens and modes.

## Platforms

Web only.

## Component Rules

Use the tokens.

## Motion Rules

Use purposeful motion and a reduced-motion equivalent.

## Responsive Behavior

Collapse navigation before content.

## Content And Imagery

Use representative content and owned imagery.

## Anti-Patterns

No unrelated styling.

## Design Change Policy

Update this file through `sp-design`.

## UI QA Checklist

Capture screenshots.

## Reference Fidelity

Bind evidence to the approved preview digest.

## Planned Gaps and Exceptions

None.
"""


def _configured_preview() -> str:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("__ROUND_NUMBER__", "1")
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
    match = re.search(
        r'<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>(.*?)</script>',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match is not None
    manifest = json.loads(match.group(1))
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
    for direction, (signature, dials, family) in zip(
        manifest["directions"],
        taste,
        strict=True,
    ):
        direction["signature_element"] = signature
        direction["dials"] = dials
        direction["aesthetic_family"] = family
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2)
    pattern = re.compile(
        r'(<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>).*?(</script>)',
        re.DOTALL | re.IGNORECASE,
    )
    updated, count = pattern.subn(
        lambda match: f"{match.group(1)}\n{rendered}\n  {match.group(2)}",
        content,
        count=1,
    )
    assert count == 1
    return updated


def _ready_design_text(tmp_path: Path, content: str = VALID_DESIGN) -> str:
    preview = tmp_path / ".specify" / "design" / "previews" / "round-01.html"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_text(_configured_preview(), encoding="utf-8")
    approval = approve_design_preview(preview, direction_id="direction-a")
    return (
        content.replace("PREVIEW_SHA256", approval["html_sha256"])
        .replace("MANIFEST_SHA256", approval["manifest_sha256"])
        .replace("HANDOFF_SHA256", approval["handoff_sha256"])
        .replace(
            "HANDOFF_CONTRACT_IDS",
            json.dumps(approval["handoff_contract_ids"]),
        )
    )


def _ready_change_design_text(
    design_path: Path,
    *,
    change_id: str,
    scopes: list[str],
    supersedes: list[str] | None = None,
    iteration_of: str | None = None,
    baseline_refs: list[str] | None = None,
) -> str:
    preview = design_path.parent / "previews" / "round-01.html"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_text(_configured_preview(), encoding="utf-8")
    approval = approve_design_preview(preview, direction_id="direction-a")
    header = (
        "design_change:\n"
        "  schema: spec-kit-ui-design-change-v1\n"
        f"  id: {change_id}\n"
        f"  title: {change_id} approved design\n"
        f"  change_type: {'overhaul' if supersedes else 'extension'}\n"
        "  scope:\n"
        f"    surfaces: {json.dumps(scopes)}\n"
        "    entrypoints: []\n"
        "    states: []\n"
        "    platforms: [web]\n"
        f"  baseline_refs: {json.dumps(baseline_refs or [])}\n"
        "  relationships:\n"
        f"    iteration_of: {json.dumps(iteration_of)}\n"
        f"    supersedes: {json.dumps(supersedes or [])}\n"
        "    depends_on: []\n"
        "    conflicts_with: []\n"
        "  constraints:\n"
        "    must_preserve: []\n"
        "    may_adapt: []\n"
        "    must_not: []\n"
    )
    content = VALID_DESIGN.replace(
        "design_system:\n  schema: spec-kit-design-v1\n",
        header,
        1,
    )
    content = content.replace(
        ".specify/design/previews/round-01.html",
        "previews/round-01.html",
    ).replace(
        ".specify/design/previews/round-01.handoff.json",
        "previews/round-01.handoff.json",
    )
    return (
        content.replace("PREVIEW_SHA256", approval["html_sha256"])
        .replace("MANIFEST_SHA256", approval["manifest_sha256"])
        .replace("HANDOFF_SHA256", approval["handoff_sha256"])
        .replace(
            "HANDOFF_CONTRACT_IDS",
            json.dumps(approval["handoff_contract_ids"]),
        )
    )


def test_parse_design_markdown_reads_yaml_front_matter() -> None:
    document = parse_design_markdown(VALID_DESIGN, source="DESIGN.md")

    assert document.design_system["schema"] == "spec-kit-design-v1"
    assert document.design_system["name"] == "test-system"
    assert document.body.startswith("# Design")


def test_scaffold_design_change_creates_change_local_contract_and_index(
    tmp_path: Path,
) -> None:
    design_path = scaffold_design_change(
        tmp_path,
        change_id="UD-0042",
        title="Orders workspace redesign",
        change_type="overhaul",
        scopes=["web:orders/list", "web:orders/detail"],
        profile_ids=["web"],
    )

    assert design_path == (
        tmp_path / ".specify" / "design" / "changes" / "UD-0042" / "DESIGN.md"
    )
    assert design_path.is_file()
    assert not (tmp_path / "DESIGN.md").exists()

    document = parse_design_markdown(
        design_path.read_text(encoding="utf-8"),
        source=str(design_path),
    )
    assert document.front_matter["design_change"]["schema"] == (
        "spec-kit-ui-design-change-v1"
    )
    assert document.design_system["id"] == "UD-0042"
    assert document.design_system["change_type"] == "overhaul"
    assert document.design_system["scope"]["surfaces"] == [
        "web:orders/list",
        "web:orders/detail",
    ]
    assert lint_design_file(design_path) == []

    index = json.loads(
        (tmp_path / ".specify" / "design" / "index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index["schema"] == "spec-kit-ui-design-index-v1"
    assert index["changes"] == [
        {
            "approval_sha256": None,
            "change_type": "overhaul",
            "consumers": [],
            "design_ref": ".specify/design/changes/UD-0042/DESIGN.md",
            "id": "UD-0042",
            "scope": ["web:orders/list", "web:orders/detail"],
            "status": "draft",
            "supersedes": [],
            "title": "Orders workspace redesign",
        }
    ]


def test_design_change_lint_rejects_invalid_iteration_source(tmp_path: Path) -> None:
    design_path = scaffold_design_change(
        tmp_path,
        change_id="UD-0042",
        title="Orders workspace redesign",
        change_type="preserve",
        scopes=["web:orders"],
        profile_ids=["web"],
    )
    design_path.write_text(
        design_path.read_text(encoding="utf-8").replace(
            "iteration_of: null", "iteration_of: not-a-change"
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_path)

    assert any(
        diagnostic.code == "invalid-design-change-iteration"
        for diagnostic in diagnostics
    )


def test_scaffold_design_change_preserves_independent_change_workspaces(
    tmp_path: Path,
) -> None:
    scaffold_design_change(
        tmp_path,
        change_id="UD-0042",
        title="Orders workspace redesign",
        change_type="overhaul",
        scopes=["web:orders"],
        profile_ids=["web"],
    )
    second = scaffold_design_change(
        tmp_path,
        change_id="UD-0043",
        title="Account settings refresh",
        change_type="preserve",
        scopes=["web:settings"],
        profile_ids=["web"],
    )

    assert second.is_file()
    index = json.loads(
        (tmp_path / ".specify" / "design" / "index.json").read_text(
            encoding="utf-8"
        )
    )
    assert [change["id"] for change in index["changes"]] == ["UD-0042", "UD-0043"]

    with pytest.raises(DesignLintError, match="already exists"):
        scaffold_design_change(
            tmp_path,
            change_id="UD-0042",
            title="Duplicate",
            change_type="overhaul",
            scopes=["web:orders"],
            profile_ids=["web"],
        )


def test_register_design_change_pins_digest_and_blocks_ambiguous_overlap(
    tmp_path: Path,
) -> None:
    first = scaffold_design_change(
        tmp_path,
        change_id="UD-0042",
        title="Orders workspace redesign",
        change_type="extension",
        scopes=["web:orders"],
        profile_ids=["web"],
    )
    first.write_text(
        _ready_change_design_text(
            first,
            change_id="UD-0042",
            scopes=["web:orders"],
        ),
        encoding="utf-8",
    )
    registered = register_design_change(tmp_path, first)

    assert registered["status"] == "approved"
    assert registered["approval_sha256"] == hashlib.sha256(
        first.read_bytes()
    ).hexdigest()

    overlapping = scaffold_design_change(
        tmp_path,
        change_id="UD-0043",
        title="Orders list refinement",
        change_type="extension",
        scopes=["web:orders/list"],
        profile_ids=["web"],
    )
    overlapping.write_text(
        _ready_change_design_text(
            overlapping,
            change_id="UD-0043",
            scopes=["web:orders/list"],
        ),
        encoding="utf-8",
    )
    with pytest.raises(DesignLintError, match="overlaps approved design change UD-0042"):
        register_design_change(tmp_path, overlapping)

    replacement = scaffold_design_change(
        tmp_path,
        change_id="UD-0044",
        title="Orders workspace overhaul",
        change_type="overhaul",
        scopes=["web:orders"],
        profile_ids=["web"],
        supersedes=["UD-0042"],
    )
    replacement.write_text(
        _ready_change_design_text(
            replacement,
            change_id="UD-0044",
            scopes=["web:orders"],
            supersedes=["UD-0042"],
        ),
        encoding="utf-8",
    )
    register_design_change(tmp_path, replacement)

    index = json.loads(
        (tmp_path / ".specify" / "design" / "index.json").read_text(
            encoding="utf-8"
        )
    )
    records = {record["id"]: record for record in index["changes"]}
    assert records["UD-0042"]["status"] == "superseded"
    assert records["UD-0042"]["superseded_by"] == "UD-0044"
    assert records["UD-0044"]["status"] == "approved"


def _create_registered_change(
    tmp_path: Path,
    change_id: str,
    scope: str,
) -> tuple[Path, str]:
    design_path = scaffold_design_change(
        tmp_path,
        change_id=change_id,
        title=f"{change_id} design",
        change_type="extension",
        scopes=[scope],
        profile_ids=["web"],
    )
    design_path.write_text(
        _ready_change_design_text(
            design_path,
            change_id=change_id,
            scopes=[scope],
        ),
        encoding="utf-8",
    )
    record = register_design_change(tmp_path, design_path)
    return design_path, str(record["approval_sha256"])


def _ready_iteration(
    design_path: Path,
    *,
    change_id: str,
    scope: str,
    source_id: str,
    source_digest: str,
) -> None:
    baseline = (
        f".specify/design/changes/{source_id}/DESIGN.md#sha256={source_digest}"
    )
    design_path.write_text(
        _ready_change_design_text(
            design_path,
            change_id=change_id,
            scopes=[scope],
            supersedes=[source_id],
            iteration_of=source_id,
            baseline_refs=[baseline],
        ),
        encoding="utf-8",
    )


def test_scaffold_design_iteration_pins_registered_source_without_mutating_it(
    tmp_path: Path,
) -> None:
    source, source_digest = _create_registered_change(
        tmp_path, "UD-0042", "web:orders"
    )
    source_before = source.read_bytes()

    successor = scaffold_design_iteration(
        tmp_path,
        source_id="UD-0042",
        change_id="UD-0043",
        title="Orders list refinement",
        scopes=["web:orders/list"],
    )

    assert source.read_bytes() == source_before
    document = parse_design_markdown(
        successor.read_text(encoding="utf-8"), source=str(successor)
    )
    expected_baseline = (
        ".specify/design/changes/UD-0042/DESIGN.md#sha256=" + source_digest
    )
    assert document.design_system["baseline_refs"] == [expected_baseline]
    assert document.design_system["relationships"]["iteration_of"] == "UD-0042"
    assert document.design_system["relationships"]["supersedes"] == ["UD-0042"]
    index = json.loads(
        (tmp_path / ".specify/design/index.json").read_text(encoding="utf-8")
    )
    record = next(row for row in index["changes"] if row["id"] == "UD-0043")
    assert record["iteration_of"] == "UD-0042"
    assert record["basis_sha256"] == source_digest


def test_partial_design_iteration_preserves_parent_and_resolves_active_scopes(
    tmp_path: Path,
) -> None:
    _, source_digest = _create_registered_change(
        tmp_path, "UD-0042", "web:orders"
    )
    successor = scaffold_design_iteration(
        tmp_path,
        source_id="UD-0042",
        change_id="UD-0043",
        title="Orders list refinement",
        scopes=["web:orders/list"],
    )
    _ready_iteration(
        successor,
        change_id="UD-0043",
        scope="web:orders/list",
        source_id="UD-0042",
        source_digest=source_digest,
    )
    register_design_change(tmp_path, successor)

    index = json.loads(
        (tmp_path / ".specify/design/index.json").read_text(encoding="utf-8")
    )
    parent = next(row for row in index["changes"] if row["id"] == "UD-0042")
    assert parent["status"] == "approved"
    assert parent["superseded_scopes"] == [
        {"scope": "web:orders/list", "by": "UD-0043"}
    ]
    assert [row["id"] for row in resolve_design_changes(tmp_path, "web:orders/list")] == [
        "UD-0043"
    ]
    assert [row["id"] for row in resolve_design_changes(tmp_path, "web:orders/detail")] == [
        "UD-0042"
    ]
    assert [row["id"] for row in resolve_design_changes(tmp_path, "web:orders")] == [
        "UD-0043",
        "UD-0042",
    ]


def test_design_iteration_rejects_scope_already_superseded_on_source(
    tmp_path: Path,
) -> None:
    _, source_digest = _create_registered_change(
        tmp_path, "UD-0042", "web:orders"
    )
    successor = scaffold_design_iteration(
        tmp_path,
        source_id="UD-0042",
        change_id="UD-0043",
        title="Orders list refinement",
        scopes=["web:orders/list"],
    )
    _ready_iteration(
        successor,
        change_id="UD-0043",
        scope="web:orders/list",
        source_id="UD-0042",
        source_digest=source_digest,
    )
    register_design_change(tmp_path, successor)

    with pytest.raises(DesignLintError, match="no longer active"):
        scaffold_design_iteration(
            tmp_path,
            source_id="UD-0042",
            change_id="UD-0044",
            title="Invalid list iteration",
            scopes=["web:orders/list/table"],
        )

    remaining = scaffold_design_iteration(
        tmp_path,
        source_id="UD-0042",
        change_id="UD-0044",
        title="Orders detail refinement",
        scopes=["web:orders/detail"],
    )
    assert remaining.is_file()


def test_design_diff_reports_lineage_scope_and_decision_delta(tmp_path: Path) -> None:
    _, source_digest = _create_registered_change(
        tmp_path, "UD-0042", "web:orders"
    )
    successor = scaffold_design_iteration(
        tmp_path,
        source_id="UD-0042",
        change_id="UD-0043",
        title="Orders list refinement",
        scopes=["web:orders/list"],
    )
    _ready_iteration(
        successor,
        change_id="UD-0043",
        scope="web:orders/list",
        source_id="UD-0042",
        source_digest=source_digest,
    )
    successor.write_text(
        successor.read_text(encoding="utf-8").replace(
            "use accessible semantic color pairs",
            "use stronger accessible semantic color pairs",
            1,
        ),
        encoding="utf-8",
    )
    register_design_change(tmp_path, successor)

    diff = diff_design_changes(tmp_path, "UD-0042", "UD-0043")

    assert diff["schema"] == "spec-kit-ui-design-diff-v1"
    assert diff["lineage"] == {
        "direct_iteration": True,
        "supersedes_source": True,
    }
    assert diff["decisions"]["changed"] == ["DS-COLOR-001"]
    assert "decisions" in diff["changed_sections"]


def test_design_impact_classes_cover_ui_dimensions_and_stable_contract_ids() -> None:
    diff = {
        "changed_sections": [
            "components",
            "content",
            "responsive",
            "verification",
        ],
        "decisions": {
            "added": ["DS-COMP-002"],
            "removed": [],
            "changed": ["DS-COMP-001"],
            "retained": [],
        },
        "handoff_contracts": {
            "added": ["DH-COMP-002"],
            "removed": ["DH-COMP-001"],
            "retained": [],
        },
    }

    assert _design_impact_classes(diff) == [
        "visual",
        "interaction",
        "component",
        "responsive",
        "content",
        "verification",
        "design-decision",
        "handoff-contract",
    ]


def test_design_adoption_requires_expected_change_and_retains_history(
    tmp_path: Path,
) -> None:
    parent, parent_digest = _create_registered_change(
        tmp_path, "UD-0042", "web:orders"
    )
    parent_contract = parent.parent / "design-contract.json"
    parent_contract.write_text(
        export_design_system(parent, export_format="json"), encoding="utf-8"
    )
    binding_ref = Path(".specify/features/001-orders/spec-contract.json")

    def write_binding(change_id: str, digest: str, contract: Path) -> str:
        target = tmp_path / binding_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "design_change_id": change_id,
                    "design_change_ref": f".specify/design/changes/{change_id}/DESIGN.md",
                    "design_change_sha256": digest,
                    "design_contract_ref": contract.relative_to(tmp_path).as_posix(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return hashlib.sha256(target.read_bytes()).hexdigest()

    parent_binding_digest = write_binding("UD-0042", parent_digest, parent_contract)
    approved_contract = parent_contract.read_text(encoding="utf-8")
    tampered_contract = json.loads(approved_contract)
    tampered_contract["title"] = "tampered export"
    parent_contract.write_text(
        json.dumps(tampered_contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(DesignLintError, match="does not match the registered design"):
        adopt_design_change(
            tmp_path,
            consumer_ref="feature:001-orders",
            change_id="UD-0042",
            scope="web:orders/detail",
            mode="formal",
            binding_ref=binding_ref,
            binding_sha256=parent_binding_digest,
            expected_change="none",
        )
    parent_contract.write_text(approved_contract, encoding="utf-8")
    adopt_design_change(
        tmp_path,
        consumer_ref="feature:001-orders",
        change_id="UD-0042",
        scope="web:orders/detail",
        mode="formal",
        binding_ref=binding_ref,
        binding_sha256=parent_binding_digest,
        expected_change="none",
    )

    successor = scaffold_design_iteration(
        tmp_path,
        source_id="UD-0042",
        change_id="UD-0043",
        title="Orders detail refinement",
        scopes=["web:orders/detail"],
    )
    _ready_iteration(
        successor,
        change_id="UD-0043",
        scope="web:orders/detail",
        source_id="UD-0042",
        source_digest=parent_digest,
    )
    successor.write_text(
        successor.read_text(encoding="utf-8").replace(
            "use accessible semantic color pairs",
            "use stronger accessible semantic color pairs",
            1,
        ),
        encoding="utf-8",
    )
    successor_record = register_design_change(tmp_path, successor)
    successor_contract = successor.parent / "design-contract.json"
    successor_contract.write_text(
        export_design_system(successor, export_format="json"), encoding="utf-8"
    )
    successor_binding_digest = write_binding(
        "UD-0043", str(successor_record["approval_sha256"]), successor_contract
    )

    with pytest.raises(DesignLintError, match="expected current change"):
        adopt_design_change(
            tmp_path,
            consumer_ref="feature:001-orders",
            change_id="UD-0043",
            scope="web:orders/detail",
            mode="formal",
            binding_ref=binding_ref,
            binding_sha256=successor_binding_digest,
            expected_change="none",
        )

    index_path = tmp_path / ".specify/design/index.json"
    index_before_impact = index_path.read_bytes()
    with pytest.raises(DesignLintError, match="expected current change"):
        impact_design_adoption(
            tmp_path,
            consumer_ref="feature:001-orders",
            change_id="UD-0043",
            scope="web:orders/detail",
            mode="formal",
            expected_change="none",
        )
    impact = impact_design_adoption(
        tmp_path,
        consumer_ref="feature:001-orders",
        change_id="UD-0043",
        scope="web:orders/detail",
        mode="formal",
        expected_change="UD-0042",
    )
    assert index_path.read_bytes() == index_before_impact
    assert impact["schema"] == "spec-kit-ui-design-impact-v1"
    assert impact["current_change_id"] == "UD-0042"
    assert impact["candidate_change_id"] == "UD-0043"
    assert impact["scope"] == "web:orders/detail"
    assert impact["impact_classes"] == [
        "visual",
        "interaction",
        "design-decision",
    ]
    assert impact["affected_decision_ids"] == ["DS-COLOR-001"]
    assert impact["affected_handoff_contract_ids"] == []
    assert impact["changed_sections"] == ["decisions"]
    assert impact["preserved_bindings"] == [
        "feature.ui_brief",
        "implementation.completed_work",
        "review.unaffected_scope_evidence",
    ]
    assert impact["invalidated_bindings"] == [
        "plan.ui_design_contract",
        "tasks.ui_contracts",
        "review.affected_scope_evidence",
    ]
    assert impact["reconcile_from"] == "plan"
    assert impact["reconciliation_actions"] == [
        "recompile_plan_ui_design_contract",
        "recompile_task_ui_contracts",
        "recapture_affected_review_evidence",
    ]
    assert re.fullmatch(r"[0-9a-f]{64}", impact["impact_sha256"])

    receipt = adopt_design_change(
        tmp_path,
        consumer_ref="feature:001-orders",
        change_id="UD-0043",
        scope="web:orders/detail",
        mode="formal",
        binding_ref=binding_ref,
        binding_sha256=successor_binding_digest,
        expected_change="UD-0042",
    )
    assert receipt["revision"] == 2
    assert receipt["previous_change_id"] == "UD-0042"
    assert receipt["design_change_id"] == "UD-0043"
    assert receipt["design_change_sha256"] == successor_record["approval_sha256"]
    for field in (
        "impact_sha256",
        "impact_classes",
        "preserved_bindings",
        "invalidated_bindings",
        "reconcile_from",
        "reconciliation_actions",
        "changed_sections",
        "affected_decision_ids",
        "affected_handoff_contract_ids",
    ):
        assert receipt[field] == impact[field]
    index = json.loads(
        (tmp_path / ".specify/design/index.json").read_text(encoding="utf-8")
    )
    assert [row["status"] for row in index["adoptions"]] == [
        "superseded",
        "current",
    ]


@pytest.mark.parametrize(
    (
        "strict_binding_shape",
        "strict_bound_change",
        "strict_confirmation_shape",
        "strict_error",
    ),
    [
        ("flat", "UD-0042", "valid", "ui_design_binding mapping"),
        (
            "masked-mismatch",
            "UD-9999",
            "valid",
            "exact-match confirmation.json",
        ),
        ("case-duplicate", "UD-0042", "valid", "exactly one"),
        ("duplicate-key", "UD-0042", "valid", "duplicate"),
        ("nested", "UD-0042", "minimal-forged", "confirmation digest"),
        (
            "nested",
            "UD-0042",
            "minimal-self-consistent",
            "decision.goal",
        ),
        ("nested", "UD-0042", "tampered-decision", "confirmation digest"),
    ],
)
def test_quick_design_adoption_requires_confirmed_exact_status_binding(
    tmp_path: Path,
    strict_binding_shape: str,
    strict_bound_change: str,
    strict_confirmation_shape: str,
    strict_error: str,
) -> None:
    design_path, design_digest = _create_registered_change(
        tmp_path, "UD-0042", "web:orders"
    )
    contract_path = design_path.parent / "design-contract.json"
    contract_path.write_text(
        export_design_system(design_path, export_format="json"), encoding="utf-8"
    )
    workspace = tmp_path / ".planning/quick/001-orders"
    workspace.mkdir(parents=True)
    binding_ref = Path(".planning/quick/001-orders/STATUS.md")

    def write_status(
        *,
        confirmed: bool,
        bound_change: str,
        bound_scope: str = "web:orders/detail",
        binding_shape: str = "nested",
    ) -> str:
        status = workspace / "STATUS.md"
        binding_lines = (
            "ui_design_binding:\n"
            f"  scope: {bound_scope}\n"
            f"  design_change_id: {bound_change}\n"
            "  design_change_ref: .specify/design/changes/UD-0042/DESIGN.md\n"
            f"  design_change_sha256: {design_digest}\n"
            "  design_contract_ref: .specify/design/changes/UD-0042/design-contract.json\n"
        )
        if binding_shape == "flat":
            binding_lines = (
                f"scope: {bound_scope}\n"
                f"design_change_id: {bound_change}\n"
                "design_change_ref: .specify/design/changes/UD-0042/DESIGN.md\n"
                f"design_change_sha256: {design_digest}\n"
                "design_contract_ref: .specify/design/changes/UD-0042/design-contract.json\n"
            )
        elif binding_shape == "masked-mismatch":
            binding_lines += (
                "\n## Notes\n\n"
                "design_change_id: UD-0042\n"
            )
        elif binding_shape == "case-duplicate":
            binding_lines += (
                "\n## UI design binding\n\n"
                "ui_design_binding:\n"
                f"  scope: {bound_scope}\n"
                f"  design_change_id: {bound_change}\n"
                "  design_change_ref: .specify/design/changes/UD-0042/DESIGN.md\n"
                f"  design_change_sha256: {design_digest}\n"
                "  design_contract_ref: .specify/design/changes/UD-0042/design-contract.json\n"
            )
        elif binding_shape == "duplicate-key":
            binding_lines = binding_lines.replace(
                f"  scope: {bound_scope}\n",
                "  scope: web:orders/summary\n"
                f"  scope: {bound_scope}\n",
                1,
            )
        status.write_text(
            "---\n"
            f"understanding_confirmed: {'true' if confirmed else 'false'}\n"
            "---\n\n"
            "## UI Design Binding\n\n"
            f"{binding_lines}"
            "note: exact source UD-0042\n",
            encoding="utf-8",
        )
        return hashlib.sha256(status.read_bytes()).hexdigest()

    def decision_payload(bound_change: str = "UD-0042") -> dict[str, object]:
        return {
            "goal": "Adopt the approved orders UI",
            "user_visible_result": "The orders detail uses the approved design",
            "scope": {
                "include": ["web:orders/detail"],
                "exclude": [],
                "defer": [],
            },
            "items": [
                {
                    "id": "Q1",
                    "deliverable": "Apply the approved orders UI",
                    "depends_on": [],
                    "acceptance": "The exact design binding is used",
                    "write_scope": ["src/orders"],
                }
            ],
            "recommended_approach": "",
            "assumptions_and_risks": [],
            "completion_evidence": [],
            "reconfirmation_trigger": "The approved design binding changes",
            "ui_confirmation": {
                "applicable": True,
                "confirmation_purpose": "Approve the orders UI direction",
                "user_and_primary_job": "Operators inspect an order",
                "target_experience": "A clear, efficient order detail",
                "acceptance_evidence": ["Bound UI capture"],
                "design_binding": {
                    "scope": "web:orders/detail",
                    "design_change_id": bound_change,
                    "design_change_ref": ".specify/design/changes/UD-0042/DESIGN.md",
                    "design_change_sha256": design_digest,
                    "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
                },
            },
        }

    def decision_digest(decision: dict[str, object]) -> str:
        raw_scope = decision.get("scope")
        scope = raw_scope if isinstance(raw_scope, dict) else {}
        raw_items = decision.get("items")
        items = raw_items if isinstance(raw_items, list) else []
        normalized_items = []
        for raw_item in sorted(
            (item for item in items if isinstance(item, dict)),
            key=lambda item: str(item.get("id") or ""),
        ):
            raw_dependencies = raw_item.get("depends_on")
            dependencies = (
                raw_dependencies if isinstance(raw_dependencies, list) else []
            )
            normalized_items.append(
                {
                    "id": str(raw_item.get("id") or ""),
                    "deliverable": str(raw_item.get("deliverable") or ""),
                    "depends_on": sorted(str(value) for value in dependencies),
                    "acceptance": str(raw_item.get("acceptance") or ""),
                }
            )
        protected = {
            "schema": "quick-confirmation-v1",
            "goal": str(decision.get("goal") or ""),
            "user_visible_result": str(
                decision.get("user_visible_result") or ""
            ),
            "scope": {
                "include": list(scope.get("include") or []),
                "exclude": list(scope.get("exclude") or []),
                "defer": list(scope.get("defer") or []),
            },
            "items": normalized_items,
            "recommended_approach": str(
                decision.get("recommended_approach") or ""
            ),
            "assumptions_and_risks": list(
                decision.get("assumptions_and_risks") or []
            ),
            "completion_evidence": list(
                decision.get("completion_evidence") or []
            ),
            "reconfirmation_trigger": str(
                decision.get("reconfirmation_trigger") or ""
            ),
            "ui_confirmation": decision.get("ui_confirmation"),
        }
        canonical = json.dumps(
            protected,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def write_confirmation(
        state: str,
        *,
        bound_change: str = "UD-0042",
        confirmation_shape: str = "valid",
    ) -> None:
        if confirmation_shape == "minimal-forged":
            decision = decision_payload(bound_change)
            confirmation = {
                "schema": "quick-confirmation-v1",
                "confirmation_mode": "full",
                "confirmation_state": state,
                "confirmation_digest": "c" * 64,
                "source": {"kind": "prompt", "semantic_delta": False},
                "decision": decision,
                "delivery": {
                    "waves": [
                        {"id": "W1", "item_ids": ["Q1"], "parallel": False}
                    ]
                },
            }
        elif confirmation_shape == "minimal-self-consistent":
            minimal_decision = {
                "ui_confirmation": decision_payload(bound_change)[
                    "ui_confirmation"
                ]
            }
            confirmation = {
                "schema": "quick-confirmation-v1",
                "confirmation_mode": "full",
                "confirmation_state": state,
                "confirmation_digest": decision_digest(minimal_decision),
                "source": {"kind": "prompt", "semantic_delta": False},
                "decision": minimal_decision,
                "delivery": {
                    "waves": [
                        {"id": "W1", "item_ids": ["Q1"], "parallel": False}
                    ]
                },
            }
        else:
            decision = decision_payload(bound_change)
            digest = decision_digest(decision)
            if confirmation_shape == "tampered-decision":
                decision["goal"] = "Tampered after confirmation"
            confirmation = {
                "schema": "quick-confirmation-v1",
                "confirmation_mode": "full",
                "confirmation_state": state,
                "confirmation_digest": digest,
                "source": {"kind": "prompt", "semantic_delta": False},
                "decision": decision,
                "delivery": {
                    "waves": [
                        {"id": "W1", "item_ids": ["Q1"], "parallel": False}
                    ]
                },
            }
        (workspace / "confirmation.json").write_text(
            json.dumps(confirmation) + "\n",
            encoding="utf-8",
        )

    staged_digest = write_status(confirmed=False, bound_change="UD-0042")
    write_confirmation("staged")
    with pytest.raises(DesignLintError, match="checkpoint must be confirmed"):
        adopt_design_change(
            tmp_path,
            consumer_ref="quick:001-orders",
            change_id="UD-0042",
            scope="web:orders/detail",
            mode="quick",
            binding_ref=binding_ref,
            binding_sha256=staged_digest,
            expected_change="none",
        )

    write_confirmation("confirmed", bound_change="UD-9999")
    confirmed_digest = write_status(confirmed=True, bound_change="UD-0042")
    with pytest.raises(DesignLintError, match="confirmed UI design binding"):
        adopt_design_change(
            tmp_path,
            consumer_ref="quick:001-orders",
            change_id="UD-0042",
            scope="web:orders/detail",
            mode="quick",
            binding_ref=binding_ref,
            binding_sha256=confirmed_digest,
            expected_change="none",
        )

    write_confirmation("confirmed", confirmation_shape=strict_confirmation_shape)
    strict_binding_digest = write_status(
        confirmed=True,
        bound_change=strict_bound_change,
        binding_shape=strict_binding_shape,
    )
    with pytest.raises(DesignLintError, match=strict_error):
        adopt_design_change(
            tmp_path,
            consumer_ref="quick:001-orders",
            change_id="UD-0042",
            scope="web:orders/detail",
            mode="quick",
            binding_ref=binding_ref,
            binding_sha256=strict_binding_digest,
            expected_change="none",
        )

    write_confirmation("confirmed")
    mismatched_digest = write_status(confirmed=True, bound_change="UD-9999")
    with pytest.raises(DesignLintError, match="exact registered change fields"):
        adopt_design_change(
            tmp_path,
            consumer_ref="quick:001-orders",
            change_id="UD-0042",
            scope="web:orders/detail",
            mode="quick",
            binding_ref=binding_ref,
            binding_sha256=mismatched_digest,
            expected_change="none",
        )

    mismatched_scope_digest = write_status(
        confirmed=True,
        bound_change="UD-0042",
        bound_scope="web:orders/summary",
    )
    with pytest.raises(DesignLintError, match="exact registered change fields"):
        adopt_design_change(
            tmp_path,
            consumer_ref="quick:001-orders",
            change_id="UD-0042",
            scope="web:orders/detail",
            mode="quick",
            binding_ref=binding_ref,
            binding_sha256=mismatched_scope_digest,
            expected_change="none",
        )

    binding_digest = write_status(confirmed=True, bound_change="UD-0042")
    receipt = adopt_design_change(
        tmp_path,
        consumer_ref="quick:001-orders",
        change_id="UD-0042",
        scope="web:orders/detail",
        mode="quick",
        binding_ref=binding_ref,
        binding_sha256=binding_digest,
        expected_change="none",
    )
    assert receipt["mode"] == "quick"
    assert receipt["binding_ref"] == binding_ref.as_posix()
    assert receipt["preserved_bindings"] == []
    assert receipt["invalidated_bindings"] == []
    assert receipt["reconcile_from"] == "quick-checkpoint"
    assert receipt["reconciliation_actions"] == [
        "confirm_quick_design_binding",
        "compile_quick_ui_work_items",
    ]


def test_quick_confirmation_digest_matches_go_cross_language_vector() -> None:
    decision = {
        "goal": "采用订单 UI <>&\u2028next",
        "user_visible_result": "顾客看到 résumé",
        "scope": {
            "include": ["web:订单/detail"],
            "exclude": ["legacy:<&>"],
            "defer": [],
        },
        "items": [
            {
                "id": "Q2",
                "deliverable": "完成 >",
                "depends_on": ["Q1"],
                "acceptance": "通过 &",
                "write_scope": ["src/ignored-two"],
            },
            {
                "id": "Q1",
                "deliverable": "实现 <",
                "depends_on": [],
                "acceptance": "截图\u2028ok",
                "write_scope": ["src/ignored-one"],
            },
        ],
        "recommended_approach": "保持简洁",
        "assumptions_and_risks": ["风险 <>&"],
        "completion_evidence": ["证据 ✓"],
        "reconfirmation_trigger": "设计变化",
        "ui_confirmation": {
            "applicable": True,
            "confirmation_purpose": "确认 <方向>",
            "user_and_primary_job": "运营 & 检查",
            "target_experience": "快速 > 清晰",
            "acceptance_evidence": ["截图\u2028完成"],
            "design_binding": {
                "scope": "web:订单/detail",
                "design_change_id": "UD-0042",
                "design_change_ref": ".specify/design/changes/UD-0042/DESIGN.md",
                "design_change_sha256": "a" * 64,
                "design_contract_ref": ".specify/design/changes/UD-0042/design-contract.json",
            },
        },
        "user_corrections": ["excluded from digest"],
    }
    expected = "44ba801bb2f538980b81e6096c9e5ff622df159a7e4d7e3564b7636dfad6388e"
    assert _quick_confirmation_digest(decision) == expected

    changed_write_scope = json.loads(json.dumps(decision, ensure_ascii=False))
    changed_write_scope["items"][0]["write_scope"] = [
        "src/changed-but-excluded"
    ]
    assert _quick_confirmation_digest(changed_write_scope) == expected


def test_lint_design_file_accepts_valid_design(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert diagnostics == []


def test_ready_lint_rejects_bootstrap_design_but_structural_lint_accepts_it(
    tmp_path: Path,
) -> None:
    design_file = tmp_path / "DESIGN.md"
    bootstrap = VALID_DESIGN.replace("name: test-system", "name: bootstrap-design-seed").replace(
        "  status: approved\n"
        "  approval:\n"
        "    status: approved\n"
        "    direction: direction-a\n",
        "  status: bootstrap\n"
        "  approval:\n"
        "    status: unapproved\n"
        "    direction: null\n",
    )
    design_file.write_text(bootstrap, encoding="utf-8")

    assert lint_design_file(design_file) == []
    diagnostics = lint_design_file(design_file, level="ready")

    assert any(item.code == "design-not-approved" for item in diagnostics)
    assert any(item.code == "generic-design-name" for item in diagnostics)


def test_ready_lint_rejects_non_string_approval_source_refs(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        _ready_design_text(
            tmp_path,
            VALID_DESIGN.replace(
                "    source_refs:\n      - src/app/page.tsx",
                "    source_refs:\n      - {}",
            ),
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file, level="ready")

    assert any(item.code == "missing-design-provenance" for item in diagnostics)


def test_ready_lint_requires_an_inspectable_approved_visual_reference(
    tmp_path: Path,
) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        _ready_design_text(
            tmp_path,
            VALID_DESIGN.replace(
                "    visual_refs:\n"
                "      - .specify/design/previews/round-01.html#direction-a\n",
                "    visual_refs: []\n",
            ),
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file, level="ready")

    assert any(
        item.code == "missing-approved-visual-reference"
        for item in diagnostics
    )


def test_lint_design_file_reports_non_file_path(tmp_path: Path) -> None:
    diagnostics = lint_design_file(tmp_path)

    assert any(d.code == "read-error" and "not a file" in d.message for d in diagnostics)


def test_lint_design_file_reports_missing_required_markdown_section(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        VALID_DESIGN.replace("## Anti-Patterns\n\nNo unrelated styling.\n\n", ""),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "missing-section" and "Anti-Patterns" in d.message for d in diagnostics)


def test_lint_design_file_reports_missing_design_change_policy(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        VALID_DESIGN.replace("## Design Change Policy\n\nUpdate this file through `sp-design`.\n\n", ""),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "missing-section" and "Design Change Policy" in d.message for d in diagnostics)


def test_lint_design_file_reports_unknown_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "{color.text.missing}"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "unknown-token-reference" for d in diagnostics)


def test_lint_design_file_reports_malformed_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "color.text.primary"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_lint_design_file_reports_unclosed_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "{color.text.primary"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_lint_design_file_reports_non_string_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace('text: "{color.text.primary}"', "text: 123"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_lint_design_file_reports_non_mapping_token_refs(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        VALID_DESIGN.replace(
            '      token_refs:\n        background: "{color.surface.canvas}"\n        text: "{color.text.primary}"',
            "      token_refs: 123",
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_export_design_system_json_returns_normalized_tokens(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(_ready_design_text(tmp_path), encoding="utf-8")

    exported = export_design_system(design_file, export_format="json")
    payload = json.loads(exported)

    assert payload["schema"] == "spec-kit-design-v1"
    assert payload["tokens"]["color"]["surface.canvas"]["value"] == "#ffffff"
    assert (
        payload["components"]["button"]["token_refs"]["text"] == "{color.text.primary}"
    )
    assert payload["accessibility"]["focus_visible"] == "required"
    assert payload["product_context"]["single_job"] == "update preferences"
    assert payload["direction_contract"]["signature_element"] == "section progress rail"


def test_export_design_system_tailwind_maps_supported_token_categories(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(_ready_design_text(tmp_path), encoding="utf-8")

    exported = export_design_system(design_file, export_format="tailwind")
    payload = json.loads(exported)

    assert payload["theme"]["extend"]["colors"]["surface-canvas"] == "#ffffff"
    assert payload["theme"]["extend"]["spacing"]["scale-4"] == "16px"
    assert payload["theme"]["extend"]["borderRadius"]["control"] == "6px"
    assert payload["theme"]["extend"]["fontFamily"]["body-family"] == "system-ui"
    assert payload["theme"]["extend"]["transitionDuration"]["duration-fast"] == "140ms"
    assert (
        payload["theme"]["extend"]["transitionTimingFunction"]["easing-standard"]
        == "cubic-bezier(.2, .8, .2, 1)"
    )


def test_export_design_system_allows_explicit_legacy_structural_escape_hatch(
    tmp_path: Path,
) -> None:
    design_file = tmp_path / "DESIGN.md"
    legacy_design = VALID_DESIGN.replace("  status: approved\n", "", 1)
    design_file.write_text(legacy_design, encoding="utf-8")

    with pytest.raises(DesignLintError, match="design-not-approved"):
        export_design_system(design_file, export_format="json")

    exported = export_design_system(
        design_file,
        export_format="json",
        require_ready=False,
    )

    assert json.loads(exported)["name"] == "test-system"


def test_export_design_system_rejects_unknown_format(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    with pytest.raises(DesignLintError):
        export_design_system(design_file, export_format="css")


def test_import_design_reference_writes_reference_summary(tmp_path: Path) -> None:
    out_dir = tmp_path / ".specify" / "design"

    result = import_design_reference(
        source="https://example.com/style",
        out_dir=out_dir,
        notes="Dense admin UI with compact tables.",
    )

    content = result.read_text(encoding="utf-8")
    assert result == out_dir / "references.md"
    assert "https://example.com/style" in content
    assert "Dense admin UI with compact tables." in content
    assert not (tmp_path / "DESIGN.md").exists()


def test_design_lint_cli_reports_success_by_default_against_cwd_design(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")

    result = runner.invoke(app, ["design", "lint"])

    assert result.exit_code == 0
    assert "DESIGN.md is valid at structural level" in result.output


def test_design_cli_exposes_explicit_iteration_commands() -> None:
    result = runner.invoke(app, ["design", "--help"])

    assert result.exit_code == 0
    for command in ("iterate", "resolve", "diff", "adopt"):
        assert command in result.output


def test_design_lint_cli_ready_accepts_approved_project_design(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("DESIGN.md").write_text(_ready_design_text(tmp_path), encoding="utf-8")

    result = runner.invoke(app, ["design", "lint", "--level", "ready"])

    assert result.exit_code == 0
    assert "valid at ready level" in result.output


def test_design_lint_cli_json_reports_diagnostics_for_invalid_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("DESIGN.md").write_text(
        VALID_DESIGN.replace("schema: spec-kit-design-v1", "schema: wrong-schema"),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["design", "lint", "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(diagnostic["code"] == "invalid-schema" for diagnostic in payload["diagnostics"])


def test_design_export_cli_json_prints_design_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("DESIGN.md").write_text(_ready_design_text(tmp_path), encoding="utf-8")

    result = runner.invoke(app, ["design", "export", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema"] == "spec-kit-design-v1"


def test_design_export_cli_allows_explicit_unapproved_legacy_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    legacy_design = VALID_DESIGN.replace("  status: approved\n", "", 1)
    Path("DESIGN.md").write_text(legacy_design, encoding="utf-8")

    blocked = runner.invoke(app, ["design", "export", "--format", "json"])
    migrated = runner.invoke(
        app,
        ["design", "export", "--format", "json", "--allow-unapproved"],
    )

    assert blocked.exit_code == 1
    assert migrated.exit_code == 0
    assert json.loads(migrated.output)["name"] == "test-system"


def test_specify_design_export_rejects_unknown_format_as_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["design", "export", "--format", "css"])

    assert result.exit_code == 2
    assert "--format must be json or tailwind" in result.output


def test_design_import_cli_writes_reference_without_root_design(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "design",
            "import",
            "https://example.com/style",
            "--notes",
            "Dense admin UI with compact tables.",
        ],
    )
    references_path = Path(".specify/design/references.md")
    references_content = references_path.read_text(encoding="utf-8")
    root_design_exists = Path("DESIGN.md").exists()

    assert result.exit_code == 0
    assert "Wrote .specify/design/references.md" in result.output
    assert "https://example.com/style" in references_content
    assert "Dense admin UI with compact tables." in references_content
    assert not root_design_exists
