from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable


class WorkflowArtifactRegistryError(ValueError):
    """Raised when the workflow artifact registry is missing or invalid."""


@dataclass(frozen=True)
class WorkflowArtifactRule:
    id: str
    path_patterns: tuple[str, ...]
    owner_cli: tuple[str, ...]
    path_hints: tuple[str, ...]
    safe_instruction_patterns: tuple[str, ...]
    forbidden_cli_patterns: tuple[str, ...]
    instruction_sources: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowArtifactAllowlistEntry:
    path: str
    artifact_id: str
    operation: str
    line_pattern: str
    reason: str


@dataclass(frozen=True)
class WorkflowArtifactRegistry:
    version: int
    artifacts: tuple[WorkflowArtifactRule, ...]
    allowlist: tuple[WorkflowArtifactAllowlistEntry, ...]


@dataclass(frozen=True)
class WorkflowArtifactViolation:
    path: Path
    line_number: int
    operation: str
    artifact_id: str
    artifact_hint: str
    owner_cli: tuple[str, ...]
    line_text: str
    message: str

    def to_payload(self) -> dict[str, object]:
        return {
            "path": self.path.as_posix(),
            "line_number": self.line_number,
            "operation": self.operation,
            "artifact_id": self.artifact_id,
            "artifact_hint": self.artifact_hint,
            "owner_cli": list(self.owner_cli),
            "line_text": self.line_text,
            "message": self.message,
        }


@dataclass(frozen=True)
class WorkflowArtifactLintReport:
    scanned_files: int
    violations: list[WorkflowArtifactViolation]

    @property
    def ok(self) -> bool:
        return not self.violations

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "scanned_files": self.scanned_files,
            "violation_count": len(self.violations),
            "violations": [item.to_payload() for item in self.violations],
        }


_OPERATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "read",
        re.compile(
            r"\b(?:check|test|determine|see)\s+(?:whether|if)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"\b(read|load|parse|inspect|query|consume|open|cat|get-content)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"\buse\b(?=[^;\n]{0,160}"
            r"(?:\bto\s+(?:assess|inspect|read|check|query|determine)\b|"
            r"\bas\s+(?:the\s+)?(?:source|input|reference|truth|state)\b))|"
            r"\b(?:include|attach|bundle)\b(?=[^;\n]{0,160}"
            r"\b(?:context|packet|bundle|teammate|reference|input|boundary)\b)|"
            r"\b(?:required\s+(?:inputs?|references?)|primary\s+inputs?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"\breview\s+(?:the\s+)?(?:contents?\s+of\s+)?"
            r"(?=[`\"']?(?:\.specify/|\.planning/|[\w.-]+\."
            r"(?:json|jsonl|ndjson|md|html)))",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"(?:^|[-*+]\s+|\b(?:run|execute|use|then|first|next)\s+)"
            r"(?:consult|examine|view)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"(?:^|[-*+]\s+|\b(?:run|execute|use|then)\s+)type(?=\s)",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"\b(?:require|readfile(?:sync)?|read_text|readalltext)\s*\("
            r"|\b(?:jq|yq|rg|grep|select-string|head|tail|less|more|stat|get-item|"
            r"test-path|get-childitem)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"(?:^|`\s*|\b(?:run|execute|use|then)\s+)(?:ls|dir|find)(?=\s)",
            re.IGNORECASE,
        ),
    ),
    (
        "read",
        re.compile(
            r"\b(?:agent|leader|worker|subagent|you)\b[^.;]{0,40}"
            r"\b(?:reads|loads|parses|inspects|queries|consumes|opens)\b",
            re.IGNORECASE,
        ),
    ),
    ("append", re.compile(r"\bappend\b", re.IGNORECASE)),
    (
        "delete",
        re.compile(
            r"\b(delete|remove|unlink|erase|truncate|purge|rm|del|remove-item)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "delete",
        re.compile(
            r"\b(?:agent|leader|worker|subagent|you)\b[^.;]{0,40}"
            r"\b(?:deletes|removes|unlinks|erases|truncates)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "rename",
        re.compile(
            r"\b(rename|relocate|mv|ren|move-item)\b|\bmove\s+(?:the\s+)?(?:file|artifact|directory|workspace)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "rename",
        re.compile(
            r"(?:^|[-*+]\s+|\b(?:run|execute|use|then|must|should)\s+)archive\b"
            r"|\barchive\s+(?:the\s+|this\s+|that\s+)?(?:file|artifact|directory|workspace|task|run)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "rename",
        re.compile(
            r"\b(?:agent|leader|worker|subagent|you)\b[^.;]{0,40}"
            r"\b(?:renames|archives|moves)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "copy",
        re.compile(
            r"\b(?:cp|copy-item)\b|\bcopy\s+(?:the\s+|this\s+|that\s+)?(?:file|artifact|directory|workspace|template|skeleton|example|`)",
            re.IGNORECASE,
        ),
    ),
    (
        "copy",
        re.compile(
            r"\b(?:agent|leader|worker|subagent|you)\b[^.;]{0,40}\bcopies\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"\b("
            r"write|create|render|generate|regenerate|update|refresh|persist|recreate|initialize|"
            r"edit|modify|mutate|patch|fill|compile|materialize|produce|maintain|replace|scaffold|"
            r"rewrite|overwrite|synchronize|populate|emit|serialize|dump|amend|merge|"
            r"touch|mkdir|new-item|set-content|add-content|out-file|tee|flush"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"(?:^|[-*+]\s+|\b(?:run|execute|use|then|first|next)\s+)author\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"\b(?:apply[_-]?patch|writefile(?:sync)?|write_text|writealltext)\b"
            r"|\b(?:sed\s+-i|perl\s+-pi)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"\b(?:agent|leader|worker|subagent|you)\b[^.;]{0,40}\b(?:writes|"
            r"creates|renders|generates|regenerates|updates|refreshes|persists|"
            r"recreates|initializes|edits|modifies|mutates|patches|fills|compiles|scaffolds|"
            r"materializes|produces|maintains|replaces|rewrites|overwrites|records|"
            r"stores|saves|authors|populates|emits|serializes|dumps|amends|merges)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"\b(?:by|before|after|when|while|then|start(?:\s+by)?|finish(?:\s+by)?|"
            r"continue(?:\s+by)?)\s+(?:directly\s+)?(?:writing|creating|rendering|"
            r"generating|updating|refreshing|persisting|recreating|initializing|editing|"
            r"modifying|mutating|patching|filling|compiling|materializing|producing|maintaining|"
            r"authoring|populating|emitting|serializing|dumping|amending|merging|flushing)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"\brecord\s+(?:the|this|status|result|decision|evidence|blocker|state|fields?|"
            r"acceptance|outcome|references?|refs?|entry|items?|obligations?|scenarios?|"
            r"contract|confirmation|progress|transition|metadata)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "write",
        re.compile(
            r"\b(?:set|store|save)\s+(?:the|this|that|new|all|only|each|one|a|an|status|state|field|value|result|evidence)\b",
            re.IGNORECASE,
        ),
    ),
)

_SCAN_SUFFIXES = {".md", ".json", ".py", ".ps1", ".sh", ".toml", ".yaml", ".yml"}
_COMMAND_GUIDANCE_ONLY_SOURCES = (
    "scripts/bash/update-agent-context.sh",
    "scripts/powershell/update-agent-context.ps1",
    "src/specify_cli/__init__.py",
    "src/specify_cli/learnings.py",
    "src/specify_cli/hooks/learning.py",
    "src/specify_cli/hooks/state_validation.py",
)


def default_workflow_artifact_scan_paths(root: Path) -> list[Path]:
    """Return live agent-facing product guidance, excluding historical design records."""

    paths = [
        root / "templates",
        root / "AGENTS.md",
        root / "README.md",
        root / "PROJECT-HANDBOOK.md",
        root / "src" / "specify_cli" / "integrations",
        *(root / source for source in _COMMAND_GUIDANCE_ONLY_SOURCES),
    ]
    docs = root / "docs"
    if docs.is_dir():
        paths.extend(sorted(docs.glob("*.md")))
        paths.append(docs / "design")
    return [path for path in paths if path.exists()]


def load_workflow_artifact_registry(path: Path) -> WorkflowArtifactRegistry:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowArtifactRegistryError(
            f"workflow artifact registry is missing: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise WorkflowArtifactRegistryError(
            f"workflow artifact registry is not valid JSON: {path}"
        ) from exc

    if not isinstance(raw, dict):
        raise WorkflowArtifactRegistryError(
            "workflow artifact registry must be an object"
        )

    version = raw.get("version")
    if not isinstance(version, int) or version < 1:
        raise WorkflowArtifactRegistryError(
            "workflow artifact registry version must be >= 1"
        )

    artifacts_raw = raw.get("artifacts")
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        raise WorkflowArtifactRegistryError(
            "workflow artifact registry artifacts must be a non-empty array"
        )

    artifacts: list[WorkflowArtifactRule] = []
    artifact_ids: set[str] = set()
    for index, item in enumerate(artifacts_raw):
        if not isinstance(item, dict):
            raise WorkflowArtifactRegistryError(
                f"artifact entry {index} must be an object"
            )
        artifact_id = _required_non_empty_string(
            item, "id", context=f"artifact {index}"
        )
        if artifact_id in artifact_ids:
            raise WorkflowArtifactRegistryError(f"duplicate artifact id: {artifact_id}")
        artifact_ids.add(artifact_id)
        path_patterns = _required_string_list(
            item, "path_patterns", context=artifact_id
        )
        owner_cli = _required_string_list(item, "owner_cli", context=artifact_id)
        path_hints = _required_string_list(item, "path_hints", context=artifact_id)
        safe_patterns = _optional_string_list(
            item, "safe_instruction_patterns", context=artifact_id
        )
        forbidden_cli_patterns = _optional_string_list(
            item, "forbidden_cli_patterns", context=artifact_id
        )
        for pattern in forbidden_cli_patterns:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise WorkflowArtifactRegistryError(
                    f"{artifact_id}.forbidden_cli_patterns contains invalid regex {pattern!r}: {exc}"
                ) from exc
        instruction_sources = _optional_string_list(
            item, "instruction_sources", context=artifact_id
        )
        artifacts.append(
            WorkflowArtifactRule(
                id=artifact_id,
                path_patterns=tuple(path_patterns),
                owner_cli=tuple(owner_cli),
                path_hints=tuple(path_hints),
                safe_instruction_patterns=tuple(safe_patterns),
                forbidden_cli_patterns=tuple(forbidden_cli_patterns),
                instruction_sources=tuple(instruction_sources),
            )
        )

    allowlist_raw = raw.get("allowlist")
    if not isinstance(allowlist_raw, list):
        raise WorkflowArtifactRegistryError(
            "workflow artifact registry allowlist must be an array"
        )

    allowlist: list[WorkflowArtifactAllowlistEntry] = []
    for index, item in enumerate(allowlist_raw):
        if not isinstance(item, dict):
            raise WorkflowArtifactRegistryError(
                f"allowlist entry {index} must be an object"
            )
        artifact_id = _required_non_empty_string(
            item, "artifact_id", context=f"allowlist entry {index}"
        )
        if artifact_id not in artifact_ids:
            raise WorkflowArtifactRegistryError(
                f"allowlist entry {index} references unknown artifact_id {artifact_id!r}"
            )
        reason = _required_non_empty_string(
            item, "reason", context=f"allowlist entry reason {index}"
        )
        allowlist.append(
            WorkflowArtifactAllowlistEntry(
                path=_required_non_empty_string(item, "path", context=reason),
                artifact_id=artifact_id,
                operation=_required_non_empty_string(item, "operation", context=reason),
                line_pattern=_required_non_empty_string(
                    item, "line_pattern", context=reason
                ),
                reason=reason,
            )
        )

    return WorkflowArtifactRegistry(
        version=version,
        artifacts=tuple(artifacts),
        allowlist=tuple(allowlist),
    )


def scan_workflow_artifact_instructions(
    paths: Iterable[Path], registry: WorkflowArtifactRegistry
) -> WorkflowArtifactLintReport:
    files = list(_iter_scan_files(paths))
    violations: list[WorkflowArtifactViolation] = []

    for path in files:
        relative_path = _normalized_path(path)
        text = path.read_text(encoding="utf-8")
        for line_number, line, detection_line in _iter_contextual_instruction_records(
            path, text
        ):
            legacy_runtime = _detect_legacy_python_runtime_invocation(
                relative_path, detection_line
            )
            if legacy_runtime is not None:
                violations.append(
                    WorkflowArtifactViolation(
                        path=path,
                        line_number=line_number,
                        operation="invoke",
                        artifact_id="legacy_python_runtime",
                        artifact_hint=legacy_runtime,
                        owner_cli=("specify-runtime <namespace> ...",),
                        line_text=line.strip(),
                        message=(
                            "Agent-facing workflow guidance invokes the legacy Python "
                            f"runtime via {legacy_runtime!r}; use specify-runtime instead."
                        ),
                    )
                )
            if _is_command_guidance_only_source(relative_path):
                continue
            invalid_runtime = _detect_invalid_runtime_invocation(detection_line)
            if invalid_runtime is not None:
                violations.append(
                    WorkflowArtifactViolation(
                        path=path,
                        line_number=line_number,
                        operation="invoke",
                        artifact_id="invalid_runtime_invocation",
                        artifact_hint=invalid_runtime,
                        owner_cli=("specify-runtime api show <capability-id>",),
                        line_text=line.strip(),
                        message=(
                            "Agent-facing workflow guidance uses an invalid runtime "
                            f"contract via {invalid_runtime!r}; use the capability's "
                            "declared inline or canonical-path option."
                        ),
                    )
                )
            transient_option = _detect_forbidden_transient_file_option(detection_line)
            if transient_option is not None:
                violations.append(
                    WorkflowArtifactViolation(
                        path=path,
                        line_number=line_number,
                        operation="write",
                        artifact_id="temporary_authoring_payload",
                        artifact_hint=transient_option,
                        owner_cli=(
                            "inline --content/--result-json or a specialized runtime owner",
                        ),
                        line_text=line.strip(),
                        message=(
                            f"Agent-facing {transient_option} handoff requires a raw temporary "
                            "file; use inline semantic input or a specialized runtime owner."
                        ),
                    )
                )
            for artifact in registry.artifacts:
                hint = _match_artifact_hint(detection_line, artifact)
                if hint is None and _is_instruction_source(relative_path, artifact):
                    operation = _detect_instruction_source_operation(detection_line)
                    if operation is not None and _line_uses_owner_cli(
                        detection_line, artifact
                    ):
                        operation = None
                    hint = f"instruction source {path.name}"
                elif hint is None:
                    continue
                else:
                    operation = _detect_artifact_operation(
                        detection_line, hint, artifact
                    )
                forbidden_cli = _detect_forbidden_cli_operation(
                    detection_line, hint, artifact
                )
                if forbidden_cli is not None:
                    if not _is_allowlisted(
                        relative_path,
                        artifact.id,
                        "submit",
                        detection_line,
                        registry,
                    ):
                        violations.append(
                            WorkflowArtifactViolation(
                                path=path,
                                line_number=line_number,
                                operation="submit",
                                artifact_id=artifact.id,
                                artifact_hint=hint,
                                owner_cli=artifact.owner_cli,
                                line_text=line.strip(),
                                message=(
                                    f"Unsupported whole-artifact CLI operation {forbidden_cli!r} "
                                    f"for registered workflow artifact {hint!r}; use its "
                                    "scaffold and targeted patch owner instead."
                                ),
                            )
                        )
                    continue
                if operation is None:
                    continue
                if _is_allowlisted(
                    relative_path, artifact.id, operation, detection_line, registry
                ):
                    continue
                violations.append(
                    WorkflowArtifactViolation(
                        path=path,
                        line_number=line_number,
                        operation=operation,
                        artifact_id=artifact.id,
                        artifact_hint=hint,
                        owner_cli=artifact.owner_cli,
                        line_text=line.strip(),
                        message=(
                            f"Direct {operation} instruction for registered workflow artifact "
                            f"{hint!r}; use owner CLI instead."
                        ),
                    )
                )

    return WorkflowArtifactLintReport(scanned_files=len(files), violations=violations)


def _detect_forbidden_cli_operation(
    line: str, hint: str, artifact: WorkflowArtifactRule
) -> str | None:
    if not artifact.forbidden_cli_patterns:
        return None
    normalized = re.sub(r"[*_`]", "", line)
    for clause in re.split(r"(?<=[;.!?])\s+", normalized):
        if not hint.startswith("instruction source "):
            if not _text_contains_hint(clause, hint):
                continue
            if _detect_named_artifact_operation(clause, hint) is None:
                continue
        for pattern in artifact.forbidden_cli_patterns:
            for match in re.finditer(pattern, clause, re.IGNORECASE):
                if not _operation_is_negated(clause, match.start()):
                    return match.group(0)
    return None


def _detect_forbidden_transient_file_option(line: str) -> str | None:
    normalized = re.sub(r"[*_`]", "", line)
    for option in (
        "--content-file",
        "--result-file",
        "--recovery-file",
        "--input",
        "--payload-file",
        "--semantic-intake-file",
        "--query-plan-file",
    ):
        match = re.search(
            rf"(?<![\w-]){re.escape(option)}(?![\w-])", normalized, re.IGNORECASE
        )
        if option == "--input":
            lowered = normalized.lower()
            runtime_prepared_claim_packet = "claim-reconcile apply" in lowered and any(
                marker in lowered
                for marker in (
                    "<preparedpacketpath>",
                    "runtime-prepared",
                    "runtime-created packet",
                    "runtime-created file",
                )
            )
            if runtime_prepared_claim_packet:
                continue
            tail = normalized[match.end() :] if match is not None else ""
            inline_json_input = bool(
                re.match(r"\s+(?:['\"]\s*)?[{\[]", tail)
                or re.match(r"\s+<(?:inline-)?(?:input-)?json>", tail, re.IGNORECASE)
            )
            if inline_json_input:
                continue
        if match is not None and not _operation_is_negated(normalized, match.start()):
            return option
    return None


def _detect_invalid_runtime_invocation(line: str) -> str | None:
    normalized = re.sub(r"[*_`]", "", line)
    command = re.search(
        r"\bspecify-runtime\s+evidence\s+register\b",
        normalized,
        re.IGNORECASE,
    )
    if command is None or _operation_is_negated(normalized, command.start()):
        return None
    if re.search(
        r"--object\s+(?:['\"]\s*)?(?:<inline(?:-json)?>|[\[{])",
        normalized,
        re.IGNORECASE,
    ):
        return "evidence register --object <inline-json>"
    return None


def _detect_legacy_python_runtime_invocation(path: str, line: str) -> str | None:
    normalized_path = path.replace("\\", "/")
    normalized = re.sub(r"[*_]", "", line)
    patterns = [
        re.compile(
            r"\bspecify\s+learning\s+(?:start|list|show|capture(?:-auto)?|promote)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bpython\s+-m\s+specify(?:cli)?\s+learning\s+"
            r"(?:start|list|show|capture(?:-auto)?|promote)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\{\{\s*specify-subcmd:(?:specify\s+)?learning\s+"
            r"(?:start|list|show|capture(?:-auto)?|promote)\b",
            re.IGNORECASE,
        ),
    ]
    if _is_agent_instruction_product_path(normalized_path):
        patterns.extend(
            [
                re.compile(
                    r"\bspecify\s+(?:artifact|workflow|tasks|plan|review|accept|"
                    r"discussion|quick|clarify|analyze|implement|cognition|hook|lane|"
                    r"design|result|deep-research|sp-teams)\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\bpython\s+-m\s+specify(?:cli)?\s+(?:artifact|workflow|tasks|"
                    r"plan|review|accept|discussion|quick|clarify|analyze|implement|"
                    r"cognition|hook|learning|lane|design|result|deep-research|sp-teams)\b",
                    re.IGNORECASE,
                ),
            ]
        )
    else:
        # Mixed human/operator documentation may legitimately describe bootstrap
        # commands. Only the agent-owned Learning verbs above are categorically
        # invalid there.
        return _first_non_negated_match(normalized, patterns)

    patterns.extend(
        [
            re.compile(r"\{\{\s*specify-subcmd:specify(?!-runtime)\b", re.IGNORECASE),
            re.compile(r"\bpython\s+-m\s+specify\b", re.IGNORECASE),
            re.compile(
                r"\b(?:run|execute|invoke|call|use|emulate)\s+`[^`\n]*\bspecify\s+"
                r"(?:artifact|workflow|tasks|plan|review|accept|discussion|quick|clarify|"
                r"analyze|implement|cognition|hook|doctor|lane|design|result|"
                r"deep-research|sp-teams)\b[^`\n]*`",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:run|execute|invoke|call|use|emulate)\s+specify\s+"
                r"(?:artifact|workflow|tasks|plan|review|accept|discussion|quick|clarify|"
                r"analyze|implement|cognition|hook|doctor|lane|design|result|"
                r"deep-research|sp-teams)\b",
                re.IGNORECASE,
            ),
        ]
    )
    return _first_non_negated_match(normalized, patterns)


def _first_non_negated_match(
    normalized: str, patterns: Iterable[re.Pattern[str]]
) -> str | None:
    for pattern in patterns:
        match = pattern.search(normalized)
        if match is None:
            continue
        if _operation_is_negated(normalized, match.start()):
            continue
        return match.group(0).strip()
    return None


def _is_agent_instruction_product_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.startswith("templates/")
        or "/templates/" in normalized
        or normalized.startswith("src/specify_cli/integrations/")
        or "/src/specify_cli/integrations/" in normalized
        or normalized.endswith("/AGENTS.md")
        or normalized == "AGENTS.md"
        or normalized.endswith("/PROJECT-HANDBOOK.md")
        or normalized == "PROJECT-HANDBOOK.md"
        or _is_command_guidance_only_source(normalized)
    )


def _is_command_guidance_only_source(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        normalized == source or normalized.endswith("/" + source)
        for source in _COMMAND_GUIDANCE_ONLY_SOURCES
    )


def _iter_scan_files(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for candidate in paths:
        if candidate.is_file():
            if candidate.suffix.lower() in _SCAN_SUFFIXES and candidate not in seen:
                seen.add(candidate)
                yield candidate
            continue
        if not candidate.exists():
            continue
        for path in sorted(p for p in candidate.rglob("*") if p.is_file()):
            if path.suffix.lower() not in _SCAN_SUFFIXES:
                continue
            if path in seen:
                continue
            seen.add(path)
            yield path


def _iter_instruction_records(path: Path, text: str) -> Iterable[tuple[int, str]]:
    lines = text.splitlines()
    suffix = path.suffix.lower()
    if suffix == ".toml":
        yield from _iter_toml_instruction_records(lines)
        return
    if suffix == ".py":
        yield from _iter_python_instruction_records(text)
        return
    if suffix != ".md":
        yield from enumerate(lines, start=1)
        return

    yield from _iter_markdown_instruction_records(lines)


def _iter_contextual_instruction_records(
    path: Path, text: str
) -> Iterable[tuple[int, str, str]]:
    """Carry imperative list introductions into their artifact-only bullets."""

    context: str | None = None
    for line_number, line in _iter_instruction_records(path, text):
        stripped = line.lstrip()
        list_item = bool(re.match(r"(?:[-*+]\s|\d+[.)]\s)", stripped))
        detection_line = f"{context} {line}" if context and list_item else line

        if not list_item:
            context = None
        if _starts_artifact_operation_list(line):
            context = line

        yield line_number, line, detection_line


def _starts_artifact_operation_list(line: str) -> bool:
    normalized = re.sub(r"[*_`]", "", line).strip()
    if not normalized:
        return False
    if re.search(
        r"(?:required\s+(?:inputs?|references?)|primary\s+inputs?)\s*:?$",
        normalized,
        re.IGNORECASE,
    ):
        return True
    if re.search(
        r"\b(?:read|inspect|query|consume|open)\s*:\s*$",
        normalized,
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(r"\buse\b.+\b(?:only\s+)?when\s*$", normalized, re.IGNORECASE)
    )


def _iter_python_instruction_records(text: str) -> Iterable[tuple[int, str]]:
    """Read rendered guidance from Python string literals, including joins."""

    try:
        tree = ast.parse(text)
    except SyntaxError:
        yield from enumerate(text.splitlines(), start=1)
        return

    def visit(node: ast.AST) -> Iterable[tuple[int, str]]:
        if isinstance(node, ast.JoinedStr):
            value = "".join(
                part.value
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
                else "<value>"
                for part in node.values
            )
            yield from offset_records(value, getattr(node, "lineno", 1))
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield from offset_records(node.value, getattr(node, "lineno", 1))
            return
        for child in ast.iter_child_nodes(node):
            yield from visit(child)

    def offset_records(value: str, source_line: int) -> Iterable[tuple[int, str]]:
        for relative_line, record in _iter_markdown_instruction_records(
            value.splitlines()
        ):
            yield source_line + relative_line - 1, record

    yield from visit(tree)


def _iter_toml_instruction_records(lines: list[str]) -> Iterable[tuple[int, str]]:
    """Yield TOML prompt bodies as logical records while preserving line numbers."""

    masked = [""] * len(lines)
    standalone: list[tuple[int, str]] = []
    delimiter: str | None = None
    for index, line in enumerate(lines):
        if delimiter is None:
            match = re.search(r'"""|\'\'\'', line)
            if match is None:
                standalone.append((index + 1, line))
                continue
            delimiter = match.group(0)
            remainder = line[match.end() :]
            closing = remainder.find(delimiter)
            if closing >= 0:
                masked[index] = remainder[:closing]
                delimiter = None
            else:
                masked[index] = remainder
            continue

        closing = line.find(delimiter)
        if closing >= 0:
            masked[index] = line[:closing]
            delimiter = None
        else:
            masked[index] = line

    records = [*standalone, *_iter_markdown_instruction_records(masked)]
    yield from sorted(records, key=lambda item: item[0])


def _iter_markdown_instruction_records(
    lines: list[str],
) -> Iterable[tuple[int, str]]:
    """Join wrapped Markdown instructions without merging separate bullets."""

    start = 0
    parts: list[str] = []
    data_fence: str | None = None

    def flush() -> tuple[int, str] | None:
        nonlocal start, parts
        if not parts:
            return None
        item = (start, " ".join(part.strip() for part in parts))
        start = 0
        parts = []
        return item

    for line_number, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        fence_match = re.match(r"(```+|~~~+)\s*([A-Za-z0-9_-]*)", stripped)
        if fence_match:
            marker = fence_match.group(1)
            if data_fence is not None:
                if marker.startswith(data_fence[0]):
                    data_fence = None
                continue
            item = flush()
            if item is not None:
                yield item
            language = fence_match.group(2).lower()
            if language in {"json", "jsonc", "toml", "xml", "yaml", "yml"}:
                data_fence = marker
                continue
        if data_fence is not None:
            continue
        if not line.strip():
            item = flush()
            if item is not None:
                yield item
            continue
        if parts and _starts_markdown_instruction(line):
            item = flush()
            if item is not None:
                yield item
        if not parts:
            start = line_number
        parts.append(line)
    item = flush()
    if item is not None:
        yield item


def _starts_markdown_instruction(line: str) -> bool:
    stripped = line.lstrip()
    return bool(
        re.match(r"(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|\|)", stripped)
        or re.match(r"[A-Za-z_][A-Za-z0-9_-]*:\s", line)
        or stripped.startswith(("```", "~~~", "---", "<!--", "{{spec-kit-include:"))
    )


def _required_non_empty_string(
    payload: dict[str, object], key: str, *, context: str
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowArtifactRegistryError(
            f"{context} {key} must be a non-empty string"
        )
    return value.strip()


def _required_string_list(
    payload: dict[str, object], key: str, *, context: str
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise WorkflowArtifactRegistryError(
            f"{context} {key} must be a non-empty array"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkflowArtifactRegistryError(
                f"{context} {key} entries must be non-empty strings"
            )
        result.append(item.strip())
    return result


def _optional_string_list(
    payload: dict[str, object], key: str, *, context: str
) -> list[str]:
    value = payload.get(key, [])
    if value == []:
        return []
    if not isinstance(value, list):
        raise WorkflowArtifactRegistryError(f"{context} {key} must be an array")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkflowArtifactRegistryError(
                f"{context} {key} entries must be non-empty strings"
            )
        result.append(item.strip())
    return result


def _detect_operation(line: str) -> str | None:
    for operation, _match in _iter_detected_operations(line):
        return operation
    return None


def _iter_detected_operations(line: str) -> Iterable[tuple[str, re.Match[str]]]:
    normalized = re.sub(r"[*_`]", "", line)
    for operation, pattern in _OPERATION_PATTERNS:
        for match in pattern.finditer(normalized):
            if operation == "read" and normalized[match.end() :].lower().startswith(
                "-only"
            ):
                continue
            if not _operation_is_negated(normalized, match.start()):
                yield operation, match


def _operation_is_negated(text: str, operation_start: int) -> bool:
    prefix = text[:operation_start]
    negations = list(
        re.finditer(
            r"\b(?:(?:do|does|did|must|should|may|will|can)\s+not|never|cannot|can't)\b",
            prefix,
            re.IGNORECASE,
        )
    )
    if not negations:
        return False
    tail = prefix[negations[-1].end() :]
    if re.search(r"\b(?:but|however|instead|except|unless)\b", tail, re.IGNORECASE):
        return False
    return len(re.findall(r"\b[\w-]+\b", tail)) <= 12


def _detect_artifact_operation(
    line: str,
    hint: str,
    artifact: WorkflowArtifactRule,
) -> str | None:
    """Detect an instruction in the clause that actually names the artifact.

    Prompt lines often contrast a forbidden artifact mutation with an allowed
    state mutation later in the sentence. Clause-local detection avoids both
    hiding the latter and flagging descriptive uses elsewhere on a long line.
    """

    if re.search(r"(?:^|\):\s*)Trigger:\s", line, re.IGNORECASE):
        return None

    clauses = re.split(r"(?<=[;.!?])\s+", line)
    for index, clause in enumerate(clauses):
        if not _text_contains_hint(clause, hint):
            continue
        operation = _detect_named_artifact_operation(clause, hint)
        if operation is not None and not _line_uses_owner_cli(clause, artifact):
            return operation
        if operation is not None or index + 1 >= len(clauses):
            continue
        following = clauses[index + 1]
        operation = _detect_anaphoric_operation(following)
        if operation is not None and not _line_uses_owner_cli(following, artifact):
            return operation
    return None


def _detect_named_artifact_operation(clause: str, hint: str) -> str | None:
    """Return only operations syntactically aimed at the named artifact."""

    normalized = re.sub(r"[*_`]", "", clause)
    normalized_hint = re.sub(r"[*_`]", "", hint)
    case_sensitive = any(char.isupper() for char in hint)
    searchable = normalized if case_sensitive else normalized.lower()
    needle = normalized_hint if case_sensitive else normalized_hint.lower()
    hint_positions = [
        match.start() for match in re.finditer(re.escape(needle), searchable)
    ]
    if not hint_positions:
        return None

    redirect_flags = 0 if case_sensitive else re.IGNORECASE
    redirect = re.search(
        rf"(?<!\S)>>?\s*[\"']?[^;\n]*{re.escape(normalized_hint)}",
        normalized,
        redirect_flags,
    )
    if redirect is not None and not _operation_is_negated(normalized, redirect.start()):
        return "write"

    for operation, match in _iter_detected_operations(clause):
        for hint_start in hint_positions:
            hint_end = hint_start + len(normalized_hint)
            if match.start() < hint_end and match.end() > hint_start:
                continue
            if match.start() <= hint_start:
                between = normalized[match.end() : hint_start]
                if len(re.findall(r"\b[\w-]+\b", between)) <= 24:
                    return operation
                continue
            between = normalized[hint_end : match.start()]
            if len(re.findall(r"\b[\w-]+\b", between)) > 6:
                continue
            if operation == "copy" and re.search(
                r"\b(?:missing|absent|does\s+not\s+exist|not\s+exist)\b",
                between,
                re.IGNORECASE,
            ):
                return operation
            if (operation != "read" and ":" in between) or re.search(
                r"\b(?:it|them|this|that|the\s+(?:file|artifact|state|record|workspace))\b",
                between,
                re.IGNORECASE,
            ):
                return operation
    return None


def _detect_anaphoric_operation(clause: str) -> str | None:
    normalized = re.sub(r"[*_`]", "", clause)
    anaphor = re.compile(
        r"\b(?:it|them|this\s+(?:file|artifact|state|record|workspace)|"
        r"that\s+(?:file|artifact|state|record|workspace)|"
        r"the\s+(?:file|artifact|state|record|workspace)|those\s+files)\b",
        re.IGNORECASE,
    )
    for operation, match in _iter_detected_operations(clause):
        before = normalized[: match.start()]
        after = normalized[match.end() :]
        preceding = list(anaphor.finditer(before))
        if preceding:
            tail = before[preceding[-1].end() :]
            if len(re.findall(r"\b[\w-]+\b", tail)) <= 24:
                return operation
        following = anaphor.search(after)
        if following is not None:
            head = after[: following.start()]
            if len(re.findall(r"\b[\w-]+\b", head)) <= 5:
                return operation
    return None


def _detect_instruction_source_operation(clause: str) -> str | None:
    """Detect mutations aimed at the artifact represented by a source template."""

    normalized = re.sub(r"[*_`]", "", clause)
    explicit_anaphor = re.compile(
        r"\b(?:this|that|the)\s+(?:file|document|artifact)\b",
        re.IGNORECASE,
    )
    for operation, match in _iter_detected_operations(clause):
        before = normalized[: match.start()]
        after = normalized[match.end() :]
        preceding = list(explicit_anaphor.finditer(before))
        if preceding:
            tail = before[preceding[-1].end() :]
            if len(re.findall(r"\b[\w-]+\b", tail)) <= 12:
                return operation
        following = explicit_anaphor.search(after)
        if following is not None:
            head = after[: following.start()]
            if len(re.findall(r"\b[\w-]+\b", head)) <= 5:
                return operation
        if match.start() <= 16 and re.match(r"\W+it\b", after, re.IGNORECASE):
            return operation
    return None


def _text_contains_hint(text: str, hint: str) -> bool:
    if any(char.isupper() for char in hint):
        return hint in text
    return hint.lower() in text.lower()


def _match_artifact_hint(line: str, artifact: WorkflowArtifactRule) -> str | None:
    for hint in artifact.path_hints:
        if _text_contains_hint(line, hint):
            return hint
    return None


def _is_instruction_source(path: str, artifact: WorkflowArtifactRule) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        normalized == source.replace("\\", "/")
        or normalized.endswith("/" + source.replace("\\", "/"))
        for source in artifact.instruction_sources
    )


def _line_uses_owner_cli(line: str, artifact: WorkflowArtifactRule) -> bool:
    # An owner command mentioned later in the same clause must not legitimize an
    # explicit raw-filesystem instruction. This closes wording such as "read it
    # directly, then use artifact show if needed" without penalizing the normal
    # negated form ("never read it directly; use artifact show"), whose direct
    # operation is filtered before this function is reached.
    if _has_positive_raw_operation(line):
        return False
    if re.search(
        r"\b(?:read|load|parse|inspect|open|review)\b[^;\n]{0,200}"
        r"\b(?:plus|and\s+then|then)\b[^;\n]{0,200}\bspecify-runtime\b",
        re.sub(r"[*_`]", "", line),
        re.IGNORECASE,
    ):
        return False
    lowered = line.lower()
    if any(owner.lower() in lowered for owner in artifact.owner_cli):
        return True
    return any(
        pattern.lower() in lowered for pattern in artifact.safe_instruction_patterns
    )


def _has_positive_raw_operation(line: str) -> bool:
    normalized = re.sub(r"[*_`]", "", line)
    raw_marker = r"(?:directly|by\s+hand|manually)"
    for _operation, match in _iter_detected_operations(line):
        before = normalized[max(0, match.start() - 48) : match.start()]
        after = normalized[match.end() : min(len(normalized), match.end() + 96)]
        if re.search(rf"\b{raw_marker}\s*$", before, re.IGNORECASE):
            return True
        if re.match(
            rf"(?:\W+[\w./-]+){{0,5}}\W+{raw_marker}\b",
            after,
            re.IGNORECASE,
        ):
            return True
        template_source = re.match(
            r"[^;\n]{0,160}\b(?:from|using|by\s+copying)\b"
            r"[^;\n]{0,100}\b(?:template|skeleton|example|assets?(?:/|\b))",
            after,
            re.IGNORECASE,
        )
        if template_source is None:
            continue
        authoring_segment = after[: template_source.end()]
        if re.search(
            r"\bspecify-runtime\s+artifact\s+scaffold\b",
            authoring_segment,
            re.IGNORECASE,
        ):
            continue
        prefix = normalized[: match.start()]
        imperative_or_agent_owned = (
            not prefix.strip(" \t-+*0123456789.():")
            or bool(
                re.search(
                    r"\b(?:agent|leader|worker|subagent|you)\b[^.;\n]{0,48}$",
                    prefix,
                    re.IGNORECASE,
                )
            )
            or bool(
                re.search(
                    r"(?:^|[.;!?]\s+)(?:first|next|then|when\s+missing|"
                    r"if\s+(?:missing|absent|needed))?\W*$",
                    prefix,
                    re.IGNORECASE,
                )
            )
        )
        if imperative_or_agent_owned:
            return True
    return False


def _is_allowlisted(
    path: str,
    artifact_id: str,
    operation: str,
    line: str,
    registry: WorkflowArtifactRegistry,
) -> bool:
    for entry in registry.allowlist:
        if (
            entry.path != path
            or entry.artifact_id != artifact_id
            or entry.operation != operation
        ):
            continue
        if re.search(entry.line_pattern, line, re.IGNORECASE):
            return True
    return False


def _normalized_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()
