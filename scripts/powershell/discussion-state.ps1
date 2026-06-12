#!/usr/bin/env pwsh
param(
    [string]$ProjectRoot = ".",
    [ValidateSet("list", "status", "rebuild-index", "close", "mark-consumed", "archive")]
    [string]$Mode = "list",
    [string]$Slug = "",
    [string]$Status = "",
    [string]$IncludeAll = "false"
)

$pythonBin = if ($env:SPECIFY_PYTHON) { $env:SPECIFY_PYTHON } else { "python" }

$pythonScript = @'
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


TERMINAL_STATUSES = {"completed", "abandoned"}
FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'", "`"}:
        return cleaned[1:-1].strip()
    return cleaned


def extract_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        match = FIELD_RE.match(raw)
        if match:
            fields[match.group(1).strip().lower()] = clean_value(match.group(2))
    return fields


def set_markdown_field(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    pattern = re.compile(rf"^(\s*-\s*{re.escape(key)}\s*:\s*).*$", re.IGNORECASE)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            lines[index] = f"{match.group(1)}{value}"
            return "\n".join(lines).rstrip() + "\n"

    insert_after = None
    for preferred in ("updated_at", "status", "slug"):
        preferred_pattern = re.compile(rf"^\s*-\s*{preferred}\s*:", re.IGNORECASE)
        for index, line in enumerate(lines):
            if preferred_pattern.match(line):
                insert_after = index
        if insert_after is not None:
            break

    new_line = f"- {key}: {value}"
    if insert_after is not None:
        lines.insert(insert_after + 1, new_line)
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["## Lifecycle", "", new_line])
    return "\n".join(lines).rstrip() + "\n"


def derive_slug(workspace: Path, fields: dict[str, str]) -> str:
    return fields.get("slug", "").strip() or workspace.name


def read_discussion(workspace: Path, archived: bool) -> dict[str, object] | None:
    state_file = workspace / "discussion-state.md"
    if not state_file.is_file():
        return None
    text = state_file.read_text(encoding="utf-8")
    fields = extract_fields(text)
    slug = derive_slug(workspace, fields)
    status = fields.get("status", "").strip().lower() or "active"
    summary = (
        fields.get("summary", "").strip()
        or fields.get("current_decision_frame", "").strip()
        or fields.get("current_topic", "").strip()
        or slug
    )
    return {
        "slug": slug,
        "workspace": workspace.name,
        "workspace_path": str(workspace),
        "status": status,
        "summary": summary,
        "current_stage": fields.get("current_stage", ""),
        "next_command": fields.get("next_command", ""),
        "updated_at": fields.get("updated_at", fields.get("updated", "")),
        "closed_at": fields.get("closed_at", ""),
        "archived_at": fields.get("archived_at", ""),
        "handoff_consumption_status": fields.get("handoff_consumption_status", ""),
        "consumed_at": fields.get("consumed_at", ""),
        "consumed_by_feature_dir": fields.get("consumed_by_feature_dir", ""),
        "archived": archived,
    }


def scan_discussions(discussion_root: Path) -> list[dict[str, object]]:
    archive_root = discussion_root / "archive"
    discussions: list[dict[str, object]] = []
    if discussion_root.exists():
        for child in sorted(discussion_root.iterdir()):
            if not child.is_dir() or child.name == "archive":
                continue
            discussion = read_discussion(child, archived=False)
            if discussion:
                discussions.append(discussion)
    if archive_root.exists():
        for child in sorted(archive_root.iterdir()):
            if not child.is_dir():
                continue
            discussion = read_discussion(child, archived=True)
            if discussion:
                discussions.append(discussion)
    return discussions


def write_index(discussion_root: Path, discussions: list[dict[str, object]]) -> dict[str, object]:
    discussion_root.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "generated_at": now_utc(), "discussions": discussions}
    (discussion_root / "index.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def match_discussion(discussions: list[dict[str, object]], slug: str) -> dict[str, object]:
    if not slug:
        raise ValueError("discussion slug is required")
    matches = [item for item in discussions if item["slug"] == slug or item["workspace"] == slug]
    if not matches:
        raise ValueError(f"discussion not found: {slug}")
    if len(matches) > 1:
        raise ValueError(f"discussion slug is ambiguous: {slug}")
    return matches[0]


def is_unclosed(discussion: dict[str, object]) -> bool:
    if bool(discussion.get("archived")):
        return False
    return str(discussion.get("status", "")).strip().lower() not in TERMINAL_STATUSES


def update_state_file(workspace: Path, updater) -> dict[str, object]:
    state_file = workspace / "discussion-state.md"
    text = state_file.read_text(encoding="utf-8")
    updated = updater(text)
    state_file.write_text(updated, encoding="utf-8")
    discussion = read_discussion(workspace, archived=False)
    if not discussion:
        raise ValueError("discussion state update failed")
    return discussion


def close_discussion(discussion: dict[str, object], status_value: str) -> None:
    if bool(discussion.get("archived")):
        raise ValueError("archived discussion cannot be closed")
    if status_value not in TERMINAL_STATUSES:
        raise ValueError("close requires status completed or abandoned")
    workspace = Path(str(discussion["workspace_path"]))
    timestamp = now_utc()

    def apply(text: str) -> str:
        text = set_markdown_field(text, "status", status_value)
        text = set_markdown_field(text, "updated_at", timestamp)
        text = set_markdown_field(text, "closed_at", timestamp)
        return text

    update_state_file(workspace, apply)


def mark_discussion_consumed(discussion: dict[str, object], consumed_by_feature_dir: str) -> None:
    if bool(discussion.get("archived")):
        raise ValueError("archived discussion cannot be marked consumed")
    status = str(discussion.get("status", "")).strip().lower()
    if status not in {"handoff-ready", "completed"}:
        raise ValueError("only handoff-ready or completed discussions can be marked consumed")
    consumed_by = consumed_by_feature_dir.strip()
    if not consumed_by:
        raise ValueError("consumed feature directory is required")

    workspace = Path(str(discussion["workspace_path"]))
    timestamp = now_utc()

    def apply(text: str) -> str:
        text = set_markdown_field(text, "status", "completed")
        text = set_markdown_field(text, "updated_at", timestamp)
        if not str(discussion.get("closed_at", "")).strip():
            text = set_markdown_field(text, "closed_at", timestamp)
        text = set_markdown_field(text, "handoff_consumption_status", "consumed")
        text = set_markdown_field(text, "consumed_at", timestamp)
        text = set_markdown_field(text, "consumed_by_feature_dir", consumed_by)
        text = set_markdown_field(text, "next_command", "none")
        return text

    update_state_file(workspace, apply)


def archive_discussion(discussion: dict[str, object], discussion_root: Path) -> dict[str, object]:
    if bool(discussion.get("archived")):
        raise ValueError("discussion is already archived")
    if str(discussion.get("status", "")).strip().lower() not in TERMINAL_STATUSES:
        raise ValueError("only completed or abandoned discussions can be archived")
    if not str(discussion.get("closed_at", "")).strip():
        raise ValueError("discussion must be closed before archive")

    archive_root = discussion_root / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    source_workspace = discussion_root / str(discussion["workspace"])
    destination = archive_root / str(discussion["workspace"])
    if destination.exists():
        raise ValueError(f"archive destination already exists: {destination.name}")

    shutil.move(str(source_workspace), str(destination))
    timestamp = now_utc()

    def apply(text: str) -> str:
        text = set_markdown_field(text, "updated_at", timestamp)
        text = set_markdown_field(text, "archived_at", timestamp)
        return text

    state_file = destination / "discussion-state.md"
    state_file.write_text(apply(state_file.read_text(encoding="utf-8")), encoding="utf-8")
    archived = read_discussion(destination, archived=True)
    if not archived:
        raise ValueError("discussion archive update failed")
    return archived


def sort_discussions(discussions: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        discussions,
        key=lambda item: (str(item.get("updated_at", "")), str(item.get("slug", ""))),
        reverse=True,
    )


def main() -> int:
    project_root = Path(sys.argv[1]).resolve()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "list").strip().lower()
    slug = (sys.argv[3] if len(sys.argv) > 3 else "").strip()
    target_status = (sys.argv[4] if len(sys.argv) > 4 else "").strip().lower()
    include_all = (sys.argv[5] if len(sys.argv) > 5 else "false").strip().lower() == "true"

    discussion_root = project_root / ".specify" / "discussions"
    discussions = scan_discussions(discussion_root)
    write_index(discussion_root, discussions)

    if mode == "rebuild-index":
        print(json.dumps(write_index(discussion_root, discussions)))
        return 0

    if mode == "list":
        selected = discussions if include_all else [item for item in discussions if is_unclosed(item)]
        print(json.dumps({"discussions": sort_discussions(selected)}))
        return 0

    if mode == "status":
        discussion = match_discussion(discussions, slug)
        print(json.dumps({"discussion": discussion}))
        return 0

    if mode == "close":
        discussion = match_discussion(discussions, slug)
        close_discussion(discussion, target_status)
        refreshed = scan_discussions(discussion_root)
        write_index(discussion_root, refreshed)
        print(json.dumps({"discussion": match_discussion(refreshed, slug)}))
        return 0

    if mode == "mark-consumed":
        discussion = match_discussion(discussions, slug)
        mark_discussion_consumed(discussion, target_status)
        refreshed = scan_discussions(discussion_root)
        write_index(discussion_root, refreshed)
        print(json.dumps({"discussion": match_discussion(refreshed, slug)}))
        return 0

    if mode == "archive":
        discussion = match_discussion(discussions, slug)
        archived = archive_discussion(discussion, discussion_root)
        refreshed = scan_discussions(discussion_root)
        write_index(discussion_root, refreshed)
        print(json.dumps({"discussion": match_discussion(refreshed, str(archived["slug"]))}))
        return 0

    raise ValueError(f"unknown mode: {mode}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
'@

$pythonScript | & $pythonBin - $ProjectRoot $Mode $Slug $Status $IncludeAll
exit $LASTEXITCODE
