from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import DebugGraphState


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "worker-prompts" / "debug-thinker.md"


def build_think_subagent_prompt(state: DebugGraphState) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    symptoms_parts: list[str] = []
    if state.symptoms.expected:
        symptoms_parts.append(f"Expected: {state.symptoms.expected}")
    if state.symptoms.actual:
        symptoms_parts.append(f"Actual: {state.symptoms.actual}")
    if state.symptoms.errors:
        symptoms_parts.append(f"Errors: {state.symptoms.errors}")
    if state.trigger:
        symptoms_parts.append(f"Trigger: {state.trigger}")

    symptoms_text = "\n".join(symptoms_parts) if symptoms_parts else "No symptoms recorded."

    feature_parts: list[str] = []
    if state.context.feature_id:
        feature_parts.append(f"Feature ID: {state.context.feature_id}")
    if state.context.summary:
        feature_parts.append(f"Summary: {state.context.summary}")
    if state.context.description:
        feature_parts.append(f"Description: {state.context.description}")
    if state.context.project_map_summary:
        feature_parts.append(f"Project Map: {state.context.project_map_summary}")
    feature_text = "\n".join(feature_parts) if feature_parts else "No feature context loaded."

    project_map_parts: list[str] = []
    if state.context.modified_files:
        project_map_parts.append("Modified files:")
        project_map_parts.extend(f"  - {f}" for f in state.context.modified_files[:10])
    if state.recently_modified:
        if not project_map_parts:
            project_map_parts.append("Recently modified files:")
        else:
            project_map_parts.append("\nRecently modified (git):")
        project_map_parts.extend(f"  - {f}" for f in state.recently_modified[:10])
    project_map_text = "\n".join(project_map_parts) if project_map_parts else "No file information available."

    prompt = (
        template
        .replace("{SYMPTOMS}", symptoms_text)
        .replace("{DIAGNOSTIC_PROFILE}", state.diagnostic_profile or "general")
        .replace("{FEATURE_CONTEXT}", feature_text)
        .replace("{PROJECT_MAP}", project_map_text)
    )

    return prompt


def parse_think_subagent_result(raw_text: str) -> dict[str, Any]:
    separator = "\n---\n"
    if separator not in raw_text:
        return {}

    _, _, yaml_block = raw_text.partition(separator)
    if not yaml_block.strip():
        return {}

    try:
        data = yaml.safe_load(yaml_block)
        if not isinstance(data, dict):
            return {}
        return data
    except yaml.YAMLError:
        return {}
