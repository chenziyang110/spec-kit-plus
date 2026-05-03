from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import DebugGraphState


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "templates"
    / "worker-prompts"
    / "debug-contract-planner.md"
)


def build_contract_subagent_prompt(state: DebugGraphState) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    causal_map = state.causal_map.model_dump(mode="json")
    observer = state.observer_framing.model_dump(mode="json")
    payload = yaml.safe_dump(
        {
            "trigger": state.trigger,
            "diagnostic_profile": state.diagnostic_profile or "general",
            "causal_map": causal_map,
            "observer_framing": observer,
        },
        allow_unicode=True,
        sort_keys=False,
    )
    return template.replace("{CAUSAL_MAP_PAYLOAD}", payload)


def parse_contract_subagent_result(raw_text: str) -> dict[str, Any]:
    separator = "\n---\n"
    if separator not in raw_text:
        return {}
    _, _, yaml_block = raw_text.partition(separator)
    if not yaml_block.strip():
        return {}
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}
