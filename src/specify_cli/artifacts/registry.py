"""Registry metadata for fixed artifact scaffold candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RECOMMENDATIONS = {
    "scaffold",
    "builder",
    "skip_low_savings",
    "skip_semantic",
    "defer_risk",
}


@dataclass(frozen=True)
class ArtifactKind:
    kind: str
    workflow: str
    artifact: str
    source_template: str
    prompt_refs: tuple[str, ...]
    allowed_output_paths: tuple[str, ...]
    fixed_anchors: tuple[str, ...]
    agent_fill_required: tuple[str, ...]
    fill_targets: dict[str, dict[str, str]]
    validator: str
    downstream_consumers: tuple[str, ...]
    package_targets: tuple[str, ...]
    scriptability: str
    quality_risk: str
    recommendation: str
    fixed_bytes_estimate: int
    semantic_bytes_estimate: int

    def audit_record(self) -> dict[str, Any]:
        total_bytes = self.fixed_bytes_estimate + self.semantic_bytes_estimate
        fixed_ratio = 0.0 if total_bytes == 0 else self.fixed_bytes_estimate / total_bytes

        return {
            "kind": self.kind,
            "workflow": self.workflow,
            "artifact": self.artifact,
            "fixed_bytes": self.fixed_bytes_estimate,
            "semantic_bytes": self.semantic_bytes_estimate,
            "fixed_ratio": round(fixed_ratio, 4),
            "estimated_token_savings": self.fixed_bytes_estimate // 4,
            "recommendation": self.recommendation,
            "scriptability": self.scriptability,
            "quality_risk": self.quality_risk,
            "agent_fill_required": list(self.agent_fill_required),
            "fill_targets": self.fill_targets,
            "validator": self.validator,
            "downstream_consumers": list(self.downstream_consumers),
            "package_targets": list(self.package_targets),
        }


ARTIFACT_REGISTRY: dict[str, ArtifactKind] = {
    "quick-status": ArtifactKind(
        kind="quick-status",
        workflow="sp-quick",
        artifact="STATUS.md",
        source_template="templates/artifacts/quick-status.md",
        prompt_refs=("templates/commands/quick.md",),
        allowed_output_paths=(".planning/quick/*/STATUS.md",),
        fixed_anchors=(
            "discussion_handoff_source",
            "current_focus",
            "execution_intent",
            "understanding_checkpoint",
            "execution",
            "validation",
            "summary_pointer",
            "senior_consequence_analysis",
        ),
        agent_fill_required=("current_focus",),
        fill_targets={
            "discussion_handoff_source": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:discussion_handoff_source",
            },
            "current_focus": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:current_focus",
            },
            "execution_intent": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:execution_intent",
            },
            "understanding_checkpoint": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:understanding_checkpoint",
            },
            "execution": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:execution",
            },
            "validation": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:validation",
            },
            "summary_pointer": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:summary_pointer",
            },
            "senior_consequence_analysis": {
                "type": "markdown_anchor",
                "anchor": "agent-fill:senior_consequence_analysis",
            },
        },
        validator="markdown-anchors",
        downstream_consumers=("sp-quick", "specify quick"),
        package_targets=("templates/artifacts",),
        scriptability="template-copy-with-anchor-fill",
        quality_risk="low",
        recommendation="scaffold",
        fixed_bytes_estimate=1600,
        semantic_bytes_estimate=240,
    ),
    "plan-contract": ArtifactKind(
        kind="plan-contract",
        workflow="sp-plan",
        artifact="plan-contract.json",
        source_template="templates/plan-contract-template.json",
        prompt_refs=("templates/commands/plan.md",),
        allowed_output_paths=(
            "specs/*/plan-contract.json",
            "specs/*/plan/plan-contract.json",
            ".specify/features/*/plan-contract.json",
            ".specify/features/*/plan/plan-contract.json",
        ),
        fixed_anchors=(),
        agent_fill_required=(
            "route",
            "intent",
            "complexity_level",
            "must_preserve",
            "acceptance_obligations",
            "allowed_optimization_scope",
        ),
        fill_targets={
            "route": {"type": "json_pointer", "pointer": "/route"},
            "intent": {"type": "json_pointer", "pointer": "/intent"},
            "complexity_level": {
                "type": "json_pointer",
                "pointer": "/complexity_level",
            },
            "must_preserve": {"type": "json_pointer", "pointer": "/must_preserve"},
            "acceptance_obligations": {
                "type": "json_pointer",
                "pointer": "/acceptance_obligations",
            },
            "allowed_optimization_scope": {
                "type": "json_pointer",
                "pointer": "/allowed_optimization_scope",
            },
        },
        validator="json",
        downstream_consumers=("sp-tasks", "sp-analyze"),
        package_targets=("templates/plan-contract-template.json",),
        scriptability="json-builder",
        quality_risk="low",
        recommendation="builder",
        fixed_bytes_estimate=900,
        semantic_bytes_estimate=320,
    ),
}


def get_artifact_kind(kind: str) -> ArtifactKind:
    try:
        return ARTIFACT_REGISTRY[kind]
    except KeyError as exc:
        raise ValueError(f"unknown artifact scaffold kind: {kind}") from exc


def _validate_allowed_output_path_pattern(
    key: str, artifact_kind: ArtifactKind, pattern: str
) -> list[str]:
    errors: list[str] = []

    if not pattern:
        return [f"{key}: allowed output path pattern is empty"]
    if "\\" in pattern:
        errors.append(
            f"{key}: allowed output path pattern must use POSIX separators: {pattern}"
        )
    if pattern.startswith("/") or (len(pattern) > 1 and pattern[1] == ":"):
        errors.append(f"{key}: allowed output path pattern must be relative: {pattern}")
    if ".." in pattern.split("/"):
        errors.append(f"{key}: allowed output path pattern cannot contain '..': {pattern}")
    if not pattern.endswith(f"/{artifact_kind.artifact}") and pattern != artifact_kind.artifact:
        errors.append(
            f"{key}: allowed output path pattern must end with "
            f"{artifact_kind.artifact}: {pattern}"
        )

    return errors


def validate_registry() -> list[str]:
    errors: list[str] = []

    for key, artifact_kind in ARTIFACT_REGISTRY.items():
        if key != artifact_kind.kind:
            errors.append(f"{key}: registry key does not match kind {artifact_kind.kind}")
        if not artifact_kind.source_template:
            errors.append(f"{key}: source_template is required")
        if not artifact_kind.allowed_output_paths:
            errors.append(f"{key}: allowed_output_paths is required")
        for pattern in artifact_kind.allowed_output_paths:
            errors.extend(
                _validate_allowed_output_path_pattern(key, artifact_kind, pattern)
            )
        if not artifact_kind.fill_targets:
            errors.append(f"{key}: fill_targets is required")
        for required_target in artifact_kind.agent_fill_required:
            if required_target not in artifact_kind.fill_targets:
                errors.append(f"{key}: required fill target missing: {required_target}")
        for target_name, target in artifact_kind.fill_targets.items():
            if not target.get("type"):
                errors.append(f"{key}: fill target {target_name} is missing type")
            if target.get("type") == "markdown_anchor" and not target.get("anchor"):
                errors.append(f"{key}: markdown fill target {target_name} is missing anchor")
            if target.get("type") == "json_pointer" and not target.get("pointer"):
                errors.append(f"{key}: json fill target {target_name} is missing pointer")
        if artifact_kind.recommendation not in RECOMMENDATIONS:
            errors.append(f"{key}: unsupported recommendation {artifact_kind.recommendation}")

    return errors


def audit_fixed_cost() -> dict[str, Any]:
    errors = validate_registry()

    return {
        "status": "blocked" if errors else "ok",
        "candidate_count": len(ARTIFACT_REGISTRY),
        "errors": errors,
        "candidates": [
            artifact_kind.audit_record() for artifact_kind in ARTIFACT_REGISTRY.values()
        ],
    }
