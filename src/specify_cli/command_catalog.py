"""Runtime-generated progressive catalog of every installed Typer operation."""

from __future__ import annotations

from collections.abc import Iterator
import re
from typing import Any

import click
import typer
from typer.core import TyperGroup, TyperOption
from typer.main import get_command

from .agent_api import AgentApiError, envelope


_READ_ONLY_OPERATIONS = frozenset(
    {
        "api.command",
        "api.commands",
        "api.handshake",
        "api.list",
        "api.schema",
        "api.show",
        "accept.closeout",
        "accept.validate",
        "artifact.audit-fixed-cost",
        "check",
        "design.lint",
        "discussion.list",
        "discussion.resume",
        "discussion.status",
        "discussion.validate-handoff",
        "eval.status",
        "extension.catalog.list",
        "extension.info",
        "extension.list",
        "extension.search",
        "integration.list",
        "implement.resume-audit",
        "review.validate",
        "hook.checkpoint",
        "hook.inject-learning",
        "hook.monitor-context",
        "hook.preflight",
        "hook.read-compaction",
        "hook.render-statusline",
        "hook.validate-artifacts",
        "hook.validate-boundary",
        "hook.validate-commit",
        "hook.validate-packet",
        "hook.validate-phase-boundary",
        "hook.validate-prompt",
        "hook.validate-read-path",
        "hook.validate-result",
        "hook.validate-session-state",
        "lane.status",
        "learning.list",
        "learning.show",
        "learning.start",
        "learning.status",
        "lint",
        "preset.catalog.list",
        "preset.info",
        "preset.list",
        "preset.resolve",
        "preset.search",
        "quick.list",
        "quick.resume",
        "quick.status",
        "result.path",
        "sp-teams.await",
        "sp-teams.doctor",
        "sp-teams.status",
        "sp-teams.watch",
        "workflow.next",
        "workflow.show",
        "version",
    }
)

_LOCAL_WRITE_OPERATIONS = frozenset(
    {
        "hook.build-compaction",
        "hook.capture-learning",
        "hook.complete-refresh",
        "hook.mark-dirty",
    }
)

_CONDITIONAL_LOCAL_WRITE_OPERATIONS = frozenset(
    {
        "hook.review-learning",
        "hook.signal-learning",
        "hook.validate-state",
        "hook.workflow-policy",
        "learning.aggregate",
    }
)

_INSPECT_BEFORE_EXECUTION_OPERATIONS = frozenset(
    {
        "design.export",
        "eval.run",
        "sp-teams.live-probe",
        "sp-teams.result-template",
    }
)

_LOCAL_WRITE_PREFIXES = (
    "accept.",
    "artifact.scaffold",
    "debug",
    "design.",
    "discussion",
    "eval.",
    "implement.",
    "learning.",
    "map-",
    "prd",
    "quick.",
    "review.",
    "result.",
    "sp-debug",
    "workflow.",
)

_HIGHER_RISK_PREFIXES = (
    "extension.",
    "init",
    "integrate",
    "integration.",
    "lane.",
    "preset.",
    "sp-teams",
)

_COMMAND_GROUP_TYPES = (click.Group, TyperGroup)
_OPTION_TYPES = (click.Option, TyperOption)


def _is_command_group(command: Any) -> bool:
    """Recognize both upstream Click and Typer's vendored Click groups."""

    return isinstance(command, _COMMAND_GROUP_TYPES)


def _summary(command: Any) -> str:
    raw = str(command.help or command.short_help or "").strip()
    if not raw:
        return "No command summary is declared."
    paragraph = raw.split("\n\n", 1)[0]
    return " ".join(paragraph.split())


def _mutation_hint(command_id: str) -> str:
    if command_id in _READ_ONLY_OPERATIONS:
        return "read-only"
    if command_id in _INSPECT_BEFORE_EXECUTION_OPERATIONS:
        return "inspect-before-execution"
    if command_id in _CONDITIONAL_LOCAL_WRITE_OPERATIONS:
        return "conditional-local-write"
    if command_id in _LOCAL_WRITE_OPERATIONS:
        return "local-write"
    if command_id.startswith("hook."):
        return "inspect-before-execution"
    if command_id.startswith(_LOCAL_WRITE_PREFIXES):
        return "local-write"
    if command_id.startswith(_HIGHER_RISK_PREFIXES):
        return "inspect-before-execution"
    return "unknown"


def _walk_commands(
    group: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], Any]]:
    for name, command in sorted(group.commands.items()):
        if getattr(command, "hidden", False):
            continue
        command_path = (*path, name)
        is_group = _is_command_group(command)
        if not is_group or command.invoke_without_command:
            yield command_path, command
        if is_group:
            yield from _walk_commands(command, command_path)


def _type_record(parameter: Any) -> dict[str, Any]:
    parameter_type = parameter.type
    record: dict[str, Any] = {"name": parameter_type.name or "value"}
    choices = getattr(parameter_type, "choices", None)
    if choices is not None:
        record["choices"] = [str(choice) for choice in choices]
        record["case_sensitive"] = bool(getattr(parameter_type, "case_sensitive", True))
    return record


def _safe_default(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)) and all(
        isinstance(item, (str, int, float, bool)) for item in value
    ):
        return list(value)
    return None


def _parameter_record(parameter: Any) -> dict[str, Any] | None:
    if getattr(parameter, "hidden", False) or not parameter.expose_value:
        return None
    if isinstance(parameter, _OPTION_TYPES):
        flags = [*parameter.opts, *parameter.secondary_opts]
        kind = "option"
        repeatable = bool(parameter.multiple or parameter.count)
    else:
        flags = []
        kind = "argument"
        repeatable = parameter.nargs == -1
    return {
        "name": parameter.name,
        "kind": kind,
        "flags": flags,
        "required": bool(parameter.required),
        "repeatable": repeatable,
        "nargs": parameter.nargs,
        "type": _type_record(parameter),
        "default": _safe_default(parameter.default),
        "help": " ".join(str(getattr(parameter, "help", "") or "").split()),
    }


def _declared_format_choices(parameter: dict[str, Any]) -> list[str]:
    choices = list(parameter["type"].get("choices", []))
    if choices:
        return choices
    help_text = str(parameter.get("help") or "").casefold()
    return [
        value
        for value in ("text", "json", "tailwind", "spawn-json")
        if re.search(
            rf"(?<![a-z0-9-]){re.escape(value)}(?![a-z0-9-])",
            help_text,
        )
    ]


def _machine_output(parameters: list[dict[str, Any]]) -> dict[str, Any]:
    format_parameter = next(
        (parameter for parameter in parameters if "--format" in parameter["flags"]),
        None,
    )
    if format_parameter is not None:
        return {
            "declared": True,
            "format_option": "--format",
            "choices": _declared_format_choices(format_parameter),
        }
    json_parameter = next(
        (parameter for parameter in parameters if "--json" in parameter["flags"]),
        None,
    )
    if json_parameter is None:
        return {"declared": False, "format_option": None, "choices": []}
    return {
        "declared": True,
        "format_option": "--json",
        "choices": ["json"],
    }


def command_catalog(app: typer.Typer) -> tuple[dict[str, Any], ...]:
    """Build the current command inventory from the actual installed app tree."""

    root = get_command(app)
    if not _is_command_group(root):
        raise AgentApiError("the Specify root command is not a command group")
    records: list[dict[str, Any]] = []
    for path, command in _walk_commands(root):
        command_id = ".".join(path)
        parameters = [
            record
            for parameter in command.params
            if (record := _parameter_record(parameter)) is not None
        ]
        records.append(
            {
                "id": command_id,
                "summary": _summary(command),
                "argv": ["specify", *path],
                "mutation_hint": _mutation_hint(command_id),
                "machine_output": _machine_output(parameters),
                "parameters": parameters,
            }
        )
    return tuple(records)


def list_command_catalog(
    app: typer.Typer,
    *,
    cursor: int = 0,
    limit: int = 20,
    query: str = "",
) -> dict[str, Any]:
    if cursor < 0:
        raise AgentApiError("cursor must be a non-negative integer")
    if limit < 1 or limit > 200:
        raise AgentApiError("limit must be an integer between 1 and 200")
    catalog = command_catalog(app)
    normalized_query = str(query or "").strip().casefold()
    matching = [
        record
        for record in catalog
        if not normalized_query
        or normalized_query in record["id"].casefold()
        or normalized_query in record["summary"].casefold()
    ]
    page = matching[cursor : cursor + limit]
    items = [
        {
            "id": record["id"],
            "summary": record["summary"],
            "mutation_hint": record["mutation_hint"],
            "show_argv": [
                "specify",
                "api",
                "command",
                record["id"],
                "--format",
                "json",
            ],
        }
        for record in page
    ]
    next_cursor = cursor + len(page)
    next_argv = []
    if next_cursor < len(matching):
        next_argv = [
            "specify",
            "api",
            "commands",
            "--cursor",
            str(next_cursor),
            "--limit",
            str(limit),
        ]
        if normalized_query:
            next_argv.extend(["--query", query])
        next_argv.extend(["--format", "json"])
    return envelope(
        "ok",
        f"Returned {len(items)} of {len(matching)} matching CLI operations.",
        data={
            "cursor": cursor,
            "limit": limit,
            "query": query,
            "total_matching": len(matching),
            "total_catalog": len(catalog),
        },
        items=items,
        next_argv=next_argv,
    )


def show_catalog_command(app: typer.Typer, command_id: str) -> dict[str, Any]:
    normalized = str(command_id or "").strip()
    record = next(
        (item for item in command_catalog(app) if item["id"] == normalized),
        None,
    )
    if record is None:
        raise AgentApiError(f"unknown CLI operation '{command_id}'")
    return envelope(
        "ok",
        f"CLI operation {normalized} expanded.",
        data=record,
        next_argv=[*record["argv"], "--help"],
    )


__all__ = ["command_catalog", "list_command_catalog", "show_catalog_command"]
