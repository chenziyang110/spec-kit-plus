"""Prepare a frozen, three-scenario desktop visual probe; never manufacture traces.

The agent must inspect real screenshots and act through its computer-use tools.
This helper only copies the isolated sample and creates the pre-execution book.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def prepare(destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=False)
    inputs = destination / "inputs"
    inputs.mkdir()
    for source in (ROOT / "tests/e2e_samples/desktop_rename.py", ROOT / "scripts/shared/e2e_scenarios.py"):
        shutil.copyfile(source, inputs / source.name)
    contract = inputs / "contract.md"
    contract.write_text(
        "A bounded visual verification sample, not full product coverage.\n"
        "Normal: rename A.txt to B.txt preserving the original bytes and taken.txt.\n"
        "External change: after entering B.txt, independently change A.txt bytes; confirmation must refuse "
        "and preserve the changed A.txt and unrelated taken.txt; B.txt must not exist.\n"
        "Recovery: enter B.txt and cancel; files must remain unchanged; reopen and confirm the same "
        "intent, producing the normal result exactly once.\n"
        "The sample already defines these invariants; only disposable sandbox files are targeted.\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("visual_probe_scenarios", inputs / "e2e_scenarios.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    sources = [{"path": p.relative_to(destination).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in sorted(inputs.iterdir()) if p.is_file()]
    source_ref = "inputs/contract.md"
    applicable = {"happy_path", "persistence_consistency", "visual_interaction", "external_mutation", "event_order", "repeat_cancel_retry"}
    operation = {"id": "rename", "title": "Disposable desktop rename", "entrypoint": "desktop_rename.py: Rename selected file",
                 "source_refs": [source_ref, "inputs/desktop_rename.py"], "assumptions": ["The selected object's identity and bytes remain unchanged"],
                 "side_effects": True,
                 "dimensions": {d: {"disposition": "applicable" if d in applicable else "not_applicable",
                                     "reason": "Explicit three-scenario visual baseline; other dimensions remain outside this book's requested scope",
                                     "source_refs": [source_ref]} for d in helper.DIMENSIONS},
                 "checkpoints": [{"id": "before-confirm", "observation": "B.txt entered, confirm not yet activated"}],
                 "events": [{"id": "modified", "change": "Replace only sandbox A.txt bytes externally",
                             "checkpoints": ["before-confirm"]}]}
    expected = {"normal": "B.txt has original sentinel bytes; A.txt absent; taken.txt unchanged",
                "modified": "Refuse rename; modified A.txt retained; B.txt absent; taken.txt unchanged",
                "recover": "Cancel leaves original files intact; reopen/confirm produces B.txt once with original bytes"}
    base = {"id": "normal", "operation": "rename", "title": "Normal rename through observed UI", "priority": "high",
            "dimensions": ["happy_path", "persistence_consistency", "visual_interaction"], "requirements": ["R-preserve"],
            "technique": ["state-transition"], "preconditions": ["New sample sandbox with A.txt sentinel and taken.txt unrelated bytes"],
            "steps": [{"id": "open", "actor": "visual-model", "action": "Inspect main screen and open rename for A.txt", "observe": "A.txt dialog is visible"},
                      {"id": "enter", "actor": "visual-model", "action": "Enter B.txt into the observed focused name field", "observe": "B.txt is visible before confirmation"},
                      {"id": "confirm", "actor": "visual-model", "action": "Confirm from the current observed dialog", "observe": "Inspect resulting status and files"}],
            "perturbations": [], "oracles": [{"id": "ui", "channel": "visual", "assertion": "UI reports the specified outcome", "check": "Inspect actual final screenshot"},
                                                {"id": "storage", "channel": "filesystem", "assertion": expected["normal"], "check": "Independently read sandbox filenames and exact bytes"}],
            "execution": "visual", "cleanup": ["Close only the sample process; retain hashed screenshots, actions and readback evidence"],
            "safety": ["All writes are confined to this newly created sandbox"], "condition_bindings": []}
    scenarios = []
    for identity in expected:
        row = deepcopy(base)
        row["id"] = identity
        row["title"] = identity + " visual desktop baseline"
        row["oracles"][1]["assertion"] = expected[identity]
        if identity == "modified":
            row["dimensions"] = ["external_mutation", "event_order", "persistence_consistency", "visual_interaction"]
            row["steps"].insert(2, {"id": "inject", "actor": "fixture", "action": "Change sandbox A.txt bytes after entering B.txt", "observe": "Independently read changed bytes before confirmation"})
            row["perturbations"] = [{"event": "modified", "checkpoint": "before-confirm", "step_id": "inject"}]
        if identity == "recover":
            row["dimensions"].append("repeat_cancel_retry")
            row["steps"].insert(2, {"id": "cancel", "actor": "visual-model", "action": "Cancel and independently read unchanged files", "observe": "Dialog closes, original files retained"})
            row["steps"].insert(3, {"id": "reopen", "actor": "visual-model", "action": "Reopen A.txt rename and enter B.txt again", "observe": "Same intent shown in fresh dialog"})
        scenarios.append(row)
    conditions = []
    for dimension in sorted(applicable - {"external_mutation", "event_order"}):
        variants = [{"id": row["id"], "input": row["title"], "expected": expected[row["id"]]}
                    for row in scenarios if dimension in row["dimensions"]]
        conditions.append({"id": "C-" + dimension, "operation": "rename", "dimension": dimension, "kind": "example",
                           "title": "Bounded " + dimension, "source_refs": [source_ref], "requirements": ["R-preserve"], "variants": variants})
        for row in scenarios:
            if dimension in row["dimensions"]:
                row["condition_bindings"].append({"condition": "C-" + dimension, "variant": row["id"],
                                                  "step_ids": ["confirm"], "oracle_ids": ["ui", "storage"]})
    book = {"schema_version": 2, "scope": "Three predeclared desktop visual baseline scenarios only", "source_revision": "visual-baseline-v1",
            "sources": sources, "requirements": [{"id": "R-preserve", "source_ref": source_ref, "assertion": "Honor the requested outcome and preserve unrelated bytes"}],
            "operations": [operation], "conditions": sorted(conditions, key=lambda c: c["id"]), "scenarios": scenarios,
            "discovery_gaps": [], "exclusions": [{"scope": "All other desktop sample cases and platforms", "reason": "Not requested in this bounded visual baseline", "owner": "baseline leader"}]}
    design = helper.check(book, destination)
    if design["claim"] != "scenario_design_ready":
        raise ValueError(design)
    (destination / "book.json").write_text(json.dumps(book, indent=2), encoding="utf-8")
    (destination / "design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    return {"book_sha256": design["book_sha256"], "scenario_count": 3, "condition_count": len(design["condition_obligations"]),
            "timing_count": len(design["timing_obligations"]), "source_hashes": sources}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.destination.resolve()), indent=2))
