"""Source contract checks, not an installed renderer or an agent evaluation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QuickAdaptiveGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT / "templates/advanced-skills/spx-quick"
        cls.skill = " ".join((base / "SKILL.md").read_text(encoding="utf-8").split())
        cls.contract = " ".join((base / "references/task-contract.md").read_text(encoding="utf-8").split())

    def test_direct_path_is_capability_negotiated_and_not_fake_fallback(self):
        for text in ("execution_contract.schema: quick-item-dispatch-v1",
                     "result_submit_required: true", "Missing, unknown,",
                     "never probe support", "not `blocked_dispatch` or `allow-inline`"):
            self.assertIn(text, self.skill)

    def test_selection_does_not_replace_confirmation_or_review(self):
        for text in ("After checkpoint confirmation", "low-risk", "File count",
                     "independently required review", "execution guard", "work_claim",
                     "must run and record RED", "cognition closeout **before** close"):
            self.assertIn(text, self.skill)
        self.assertIn("preserves the full confirmed Quick workspace", self.contract)
        self.assertIn("only `accepted` satisfies a", self.contract)

    def test_no_conflicting_mandatory_worker_directives_remain(self):
        for text in ("MUST spawn_subagent", "mandatory native-subagent execution",
                     "Only then start the next Q", "does **not** waive subagent-first"):
            self.assertNotIn(text, self.skill)
        self.assertNotIn("**spawn subagent** (no Leader write_scope", self.contract)

    def test_structured_results_and_active_owner_are_preserved(self):
        for text in ("result submit", "validation_results", "blockers",
                     "Resume preserves", "active worker", "leader-direct"):
            self.assertIn(text, self.skill)
            self.assertIn(text, self.contract)

    def test_existing_boundaries_remain(self):
        for text in ("## Hard preflight stop", "exact two-option menu",
                     "source_continuity", "test_design_gate", "ui_design_binding",
                     "**Terminal order is mandatory", "independent top-level"):
            self.assertIn(text, self.skill)
        self.assertIn("## Complete source consumption for direct delivery", self.contract)


if __name__ == "__main__":
    unittest.main()
