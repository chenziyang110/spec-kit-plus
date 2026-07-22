from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADVANCED = ROOT / "templates" / "advanced-skills"


def _surface(name: str) -> str:
    skill_dir = ADVANCED / f"spx-{name}"
    paths = [skill_dir / "SKILL.md"]
    paths.extend(sorted((skill_dir / "references").glob("*.md")))
    paths.extend(sorted((skill_dir / "assets").glob("*.md")))
    content = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    return " ".join(content.replace("`", "").split())


def test_implement_preserves_state_external_evidence_and_handoff_boundaries() -> None:
    content = _surface("implement")

    assert "workflow.json is the required phase gate" in content
    assert "workflow-state.md is the phase gate" not in content
    assert "external-evidence-checkpoint" in content
    assert "mandatory_for_completion" in content
    assert "every cross-workflow route is a handoff-and-stop boundary" in content


def test_implement_teams_reuses_ordinary_execution_and_resume_contract() -> None:
    content = _surface("implement-teams")

    assert "../spx-implement/references/execution-contract.md" in content
    assert "analyze gate" in content and "$spx-analyze" in content
    assert "external-evidence-checkpoint" in content
    assert "remaining planned validation tasks are ready work" in content
    assert "baseline debt" in content
    assert "stale lane" in content


def test_integrate_is_readiness_closeout_not_implicit_merge() -> None:
    content = _surface("integrate")

    assert "does not authorize a git merge" in content
    assert "do not run merge, rebase, cherry-pick" in content
    assert "do not edit conflict markers" in content
    assert "handoff and stop" in content


def test_debug_preserves_durable_intake_red_human_verify_and_recovery() -> None:
    content = _surface("debug")

    assert "durable source of truth" in content
    assert "understanding_confirmed: false" in content
    assert "before reproduction, log review, source or test reads" in content
    assert "failing automated reproduction" in content
    assert "smallest viable test harness" in content
    assert "awaiting_human_verify" in content
    assert all(value in content for value in ("same_issue", "derived_issue", "unrelated_issue"))
    assert "two failed verification cycles" in content
    assert "related-risk" in content
    assert "archive" in content and "human confirmation" in content


def test_fast_requires_red_or_escalates_and_guards_sensitive_paths() -> None:
    content = _surface("fast")

    assert "must run a failing automated test or executable repro" in content
    assert "no reliable automated test surface" in content
    assert "hand off to $spx-quick or $spx-specify and stop" in content
    assert "resolved path remains inside the repository" in content
    assert "credential, secret, private key" in content


def test_quick_uses_scaffold_checkpoint_handoff_and_full_propagation_sweep() -> None:
    content = _surface("quick")

    assert "artifact scaffold --kind quick-status" in content
    assert "understanding_confirmed: false" in content
    assert "wait for user confirmation" in content
    assert "handoff-to-specify.json" in content
    assert "consumer_eligibility.sp-quick.status" in content
    assert ".specify/memory/constitution.md" in content
    assert "project-learning cli intake" in content
    assert "task-relevant learning only through" in content
    assert "must run and record red before production edits" in content
    assert "full affected-surface or callsite coverage" in content
    assert "quick close" in content and "terminal truth" in content


def test_taskstoissues_binds_external_writes_to_the_exact_github_remote() -> None:
    content = _surface("taskstoissues")

    assert "git config --get remote.origin.url" in content
    assert "canonical github repository identity" in content
    assert "exactly matches" in content
    assert "do not create or update any issue" in content


def test_constitution_preserves_memory_versioning_sync_impact_and_reentry() -> None:
    content = _surface("constitution")

    assert "consume-only learning cli intake" in content
    assert "references/project-learning.md" in content
    assert all(name in content for name in ("spec.md", "plan.md", "tasks.md", "workflow-state.md"))
    assert "major" in content and "minor" in content and "patch" in content
    assert "yyyy-mm-dd" in content
    assert "sync impact report" in content
    assert "highest affected downstream stage" in content
    assert "pending follow-up" in content
