from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").lower()


def _read_tree(relative: str) -> str:
    directory = ROOT / relative
    assert directory.is_dir(), f"missing review contract directory: {relative}"
    files = sorted(directory.rglob("*.md"))
    assert files, f"review contract directory is empty: {relative}"
    return "\n".join(path.read_text(encoding="utf-8").lower() for path in files)


@pytest.mark.parametrize(
    "relative",
    (
        "templates/commands/review.md",
        "templates/advanced-skills/spx-review/SKILL.md",
    ),
)
def test_review_workflow_surfaces_exist(relative: str) -> None:
    assert (ROOT / relative).is_file(), f"missing required review surface: {relative}"


def test_classic_review_proves_real_product_paths_and_repairs_findings() -> None:
    combined = "\n".join(
        (
            _read("templates/commands/review.md"),
            _read_tree("templates/command-partials/review"),
            _read_tree("templates/command-references/review"),
        )
    )

    # A review is a system-level usability gate, not another source-only audit.
    assert "real entrypoint" in combined or "real entry point" in combined
    assert "user journey" in combined
    for wiring_term in ("button", "route", "handler", "provider"):
        assert wiring_term in combined
    for evidence_kind in (
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
    ):
        assert evidence_kind in combined

    # An understood defect is repaired in this stage and its exact path is rerun.
    assert "finding" in combined
    assert "repair" in combined
    assert "revalid" in combined or "rerun" in combined or "re-run" in combined
    assert "sp-debug" in combined


def test_classic_review_uses_jit_subagent_packets_but_keeps_final_authority() -> None:
    combined = "\n".join(
        (
            _read("templates/commands/review.md"),
            _read_tree("templates/command-references/review"),
        )
    )

    assert "systemreviewpacket" in combined or "system review packet" in combined
    assert "just in time" in combined or "just-in-time" in combined
    assert "subagent" in combined or "worker" in combined
    assert "leader" in combined
    assert "final verdict" in combined
    assert "worker" in combined and (
        "must not declare" in combined
        or "cannot declare" in combined
        or "never authority" in combined
    )


def test_classic_review_final_claim_requires_fresh_integrated_evidence() -> None:
    combined = "\n".join(
        (
            _read("templates/commands/review.md"),
            _read_tree("templates/command-references/review"),
        )
    )

    assert "fingerprint" in combined or "source revision" in combined
    assert "stale" in combined
    assert "blocking finding" in combined or "blocking findings" in combined
    assert "mandatory scenario" in combined or "required scenario" in combined
    assert "{{invoke:accept}}" in combined
    assert "do not claim" in combined or "never claim" in combined


def test_spx_review_preserves_the_system_review_and_repair_contract() -> None:
    combined = "\n".join(
        (
            _read("templates/advanced-skills/spx-review/SKILL.md"),
            _read_tree("templates/advanced-skills/spx-review/references"),
        )
    )

    assert "real entrypoint" in combined or "real entry point" in combined
    assert "user journey" in combined
    for wiring_term in ("button", "route", "handler", "provider"):
        assert wiring_term in combined
    assert "finding" in combined and "repair" in combined
    assert "revalid" in combined or "rerun" in combined or "re-run" in combined
    assert "systemreviewpacket" in combined or "system review packet" in combined
    assert "leader" in combined and "final verdict" in combined
    assert "blocking finding" in combined or "blocking findings" in combined
    assert "fingerprint" in combined or "source revision" in combined
    assert "$spx-debug" in combined
    assert "$spx-accept" in combined


def test_implement_hands_off_to_review_instead_of_acceptance() -> None:
    classic = _read("templates/commands/implement.md")
    advanced = _read("templates/advanced-skills/spx-implement/SKILL.md")

    assert "{{invoke:review}}" in classic
    assert "{{invoke:accept}}" not in classic
    assert "$spx-review" in advanced
    assert "recommend `$spx-accept`" not in advanced
    assert "stop" in classic and "stop" in advanced


def test_accept_requires_a_fresh_passed_review_and_routes_repairs_back_to_review() -> None:
    classic = "\n".join(
        (
            _read("templates/commands/accept.md"),
            _read_tree("templates/command-partials/accept"),
        )
    )
    advanced = "\n".join(
        (
            _read("templates/advanced-skills/spx-accept/SKILL.md"),
            _read_tree("templates/advanced-skills/spx-accept/references"),
        )
    )

    for content, review_route in (
        (classic, "{{invoke:review}}"),
        (advanced, "$spx-review"),
    ):
        assert "review" in content and "passed" in content
        assert "fingerprint" in content or "fresh" in content
        assert review_route in content

    assert "transition from `review`" in classic
    assert "transition from the validated\n`review`" in advanced or (
        "transition from the validated `review`" in advanced
    )
