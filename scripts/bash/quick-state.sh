#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-.}"
MODE="${2:-list}"
QUICK_ID="${3:-}"
TARGET_STATUS="${4:-}"
INCLUDE_ALL="${5:-false}"

python - "$PROJECT_ROOT" "$MODE" "$QUICK_ID" "$TARGET_STATUS" "$INCLUDE_ALL" <<'PY'
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    lines = text.splitlines()
    if len(lines) < 3:
        return {}, text
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text
    frontmatter_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])
    if text.endswith("\n"):
        body += "\n"
    frontmatter: dict[str, str] = {}
    for raw in frontmatter_lines:
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        frontmatter[key] = value
    return frontmatter, body


def emit_frontmatter(path: Path, frontmatter: dict[str, str], body: str) -> None:
    order = [
        "id",
        "slug",
        "title",
        "status",
        "trigger",
        "updated",
        "closed_at",
        "archived_at",
    ]
    output = ["---"]
    for key in order:
        if key in frontmatter and str(frontmatter[key]).strip():
            value = str(frontmatter[key]).strip()
            output.append(f'{key}: "{value}"')
    for key in sorted(frontmatter.keys()):
        if key in order:
            continue
        value = str(frontmatter[key]).strip()
        output.append(f'{key}: "{value}"')
    output.append("---")
    text = "\n".join(output) + "\n"
    text += body if body else ""
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def extract_named_field(body: str, field_name: str) -> str:
    prefix = f"{field_name}:"
    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.lower().startswith(prefix.lower()):
            return stripped[len(prefix):].strip()
    return ""


def extract_next_action(body: str) -> str:
    inline_value = extract_named_field(body, "next_action")
    if inline_value:
        return inline_value
    lines = body.splitlines()
    heading_re = re.compile(r"^##+\s*next action\s*$", re.IGNORECASE)
    any_heading_re = re.compile(r"^##+\s+")
    in_section = False
    for line in lines:
        if not in_section:
            if heading_re.match(line.strip()):
                in_section = True
            continue
        if any_heading_re.match(line.strip()):
            break
        cleaned = line.strip().lstrip("-*").strip()
        if cleaned:
            return cleaned
    return ""


def extract_current_focus(body: str) -> str:
    inline_value = extract_named_field(body, "current_focus")
    if inline_value:
        return inline_value
    lines = body.splitlines()
    heading_re = re.compile(r"^##+\s*current focus\s*$", re.IGNORECASE)
    any_heading_re = re.compile(r"^##+\s+")
    in_section = False
    for line in lines:
        if not in_section:
            if heading_re.match(line.strip()):
                in_section = True
            continue
        if any_heading_re.match(line.strip()):
            break
        cleaned = line.strip().lstrip("-*").strip()
        if cleaned and not cleaned.lower().startswith(("goal:", "next_action:")):
            return cleaned
    return ""


def derive_identity(dirname: str, frontmatter: dict[str, str]) -> tuple[str, str]:
    task_id = frontmatter.get("id", "").strip()
    slug = frontmatter.get("slug", "").strip()
    if task_id and slug:
        return task_id, slug
    match = re.match(r"^([0-9]{6,8}-[0-9]{3,})-(.+)$", dirname)
    if match:
        if not task_id:
            task_id = match.group(1)
        if not slug:
            slug = match.group(2)
    elif not task_id:
        task_id = dirname
    if not slug:
        slug = dirname
    return task_id, slug


def read_task(workspace: Path, archived: bool) -> dict[str, object] | None:
    status_file = workspace / "STATUS.md"
    if not status_file.is_file():
        return None
    text = status_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    task_id, slug = derive_identity(workspace.name, frontmatter)
    status = frontmatter.get("status", "").strip().lower() or "gathering"
    title = frontmatter.get("title", "").strip() or frontmatter.get("trigger", "").strip() or slug
    task = {
        "id": task_id,
        "slug": slug,
        "workspace": workspace.name,
        "workspace_path": str(workspace),
        "status": status,
        "title": title,
        "current_focus": extract_current_focus(body),
        "next_action": extract_next_action(body),
        "updated": frontmatter.get("updated", ""),
        "closed_at": frontmatter.get("closed_at", ""),
        "archived_at": frontmatter.get("archived_at", ""),
        "archived": archived,
    }
    return task


def scan_tasks(quick_root: Path) -> list[dict[str, object]]:
    archive_root = quick_root / "archive"
    tasks: list[dict[str, object]] = []
    if quick_root.exists():
        for child in sorted(quick_root.iterdir()):
            if not child.is_dir() or child.name == "archive":
                continue
            task = read_task(child, archived=False)
            if task:
                tasks.append(task)
    if archive_root.exists():
        for child in sorted(archive_root.iterdir()):
            if not child.is_dir():
                continue
            task = read_task(child, archived=True)
            if task:
                tasks.append(task)
    return tasks


def write_index(quick_root: Path, tasks: list[dict[str, object]]) -> dict[str, object]:
    quick_root.mkdir(parents=True, exist_ok=True)
    index_path = quick_root / "index.json"
    payload = {"version": 1, "generated_at": now_utc(), "tasks": tasks}
    index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def match_task(tasks: list[dict[str, object]], quick_id: str) -> dict[str, object]:
    if not quick_id:
        raise ValueError("quick id is required")
    matches = [t for t in tasks if t["id"] == quick_id or t["workspace"] == quick_id]
    if not matches:
        raise ValueError(f"quick task not found: {quick_id}")
    if len(matches) > 1:
        raise ValueError(f"quick id is ambiguous: {quick_id}")
    return matches[0]


def is_unfinished(task: dict[str, object]) -> bool:
    if bool(task.get("archived")):
        return False
    return str(task.get("status", "")).strip().lower() != "resolved"


def update_status_file(workspace: Path, updater) -> dict[str, object]:
    status_file = workspace / "STATUS.md"
    text = status_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    updater(frontmatter, body)
    emit_frontmatter(status_file, frontmatter, body)
    task = read_task(workspace, archived=False)
    if not task:
        raise ValueError("status file update failed")
    return task


def close_task(task: dict[str, object], status_value: str) -> None:
    if status_value not in {"resolved", "blocked"}:
        raise ValueError("close requires status resolved or blocked")
    workspace = Path(str(task["workspace_path"]))

    def apply(frontmatter: dict[str, str], _body: str) -> None:
        frontmatter["status"] = status_value
        frontmatter["updated"] = now_utc()
        frontmatter["closed_at"] = now_utc()

    update_status_file(workspace, apply)


def archive_task(task: dict[str, object], quick_root: Path) -> dict[str, object]:
    if bool(task.get("archived")):
        raise ValueError("quick task is already archived")
    if str(task.get("status", "")).strip().lower() not in {"resolved", "blocked"}:
        raise ValueError("only resolved or blocked quick tasks can be archived")
    if not str(task.get("closed_at", "")).strip():
        raise ValueError("quick task must be closed before archive")

    archive_root = quick_root / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    source_workspace = quick_root / str(task["workspace"])
    destination = archive_root / str(task["workspace"])
    if destination.exists():
        raise ValueError(f"archive destination already exists: {destination.name}")

    shutil.move(str(source_workspace), str(destination))

    def apply(frontmatter: dict[str, str], _body: str) -> None:
        frontmatter["archived_at"] = now_utc()
        frontmatter["updated"] = now_utc()

    archived_task = update_status_file(destination, apply)
    archived_task["archived"] = True
    return archived_task


def main() -> int:
    project_root = Path(sys.argv[1]).resolve()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "list").strip().lower()
    quick_id = (sys.argv[3] if len(sys.argv) > 3 else "").strip()
    target_status = (sys.argv[4] if len(sys.argv) > 4 else "").strip().lower()
    include_all = (sys.argv[5] if len(sys.argv) > 5 else "false").strip().lower() == "true"

    quick_root = project_root / ".planning" / "quick"
    tasks = scan_tasks(quick_root)
    write_index(quick_root, tasks)

    if mode == "rebuild-index":
        print(json.dumps(write_index(quick_root, tasks)))
        return 0

    if mode == "list":
        if include_all:
            selected = tasks
        else:
            selected = [task for task in tasks if is_unfinished(task)]
        selected = sorted(selected, key=lambda x: (str(x.get("id", "")), str(x.get("workspace", ""))))
        print(json.dumps({"tasks": selected}))
        return 0

    if mode == "status":
        task = match_task(tasks, quick_id)
        print(json.dumps({"task": task}))
        return 0

    if mode == "close":
        task = match_task(tasks, quick_id)
        close_task(task, target_status)
        refreshed_tasks = scan_tasks(quick_root)
        write_index(quick_root, refreshed_tasks)
        refreshed = match_task(refreshed_tasks, quick_id)
        print(json.dumps({"task": refreshed}))
        return 0

    if mode == "archive":
        task = match_task(tasks, quick_id)
        archived = archive_task(task, quick_root)
        refreshed_tasks = scan_tasks(quick_root)
        write_index(quick_root, refreshed_tasks)
        refreshed = match_task(refreshed_tasks, str(archived["workspace"]))
        print(json.dumps({"task": refreshed}))
        return 0

    raise ValueError(f"unknown mode: {mode}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
PY
