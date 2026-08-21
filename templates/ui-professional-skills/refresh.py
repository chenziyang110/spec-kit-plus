from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

selected_only = ["material-ui", "ag-grid", "tiptap"]
offline_default = True
allowed_source_kinds = {"agent-skill", "mcp", "llms-txt", "markdown"}

INSTALL_POLICY = "unauthorized"
UPGRADE_POLICY = "unauthorized"
NETWORK_POLICY = "blocked_by_default"

_selected_only_enabled = True

_WHITESPACE_RE = re.compile(r"\s+")


def normalized_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip()).casefold()


def normalized_hash(value: str) -> str:
    payload = normalized_text(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def _validate_source(item: dict[str, Any]) -> dict[str, str]:
    resource_id = item.get("resource_id")
    source_kind = item.get("source_kind")
    source_url = item.get("source_url")
    if not isinstance(resource_id, str) or not resource_id:
        raise ValueError("snapshot item missing resource_id")
    if source_kind not in allowed_source_kinds:
        raise ValueError(f"unsupported source_kind: {source_kind!r}")
    if not isinstance(source_url, str) or not source_url:
        raise ValueError(f"snapshot item {resource_id!r} missing source_url")
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"snapshot item {resource_id!r} must use an official http(s) URL")
    return {
        "resource_id": resource_id,
        "source_kind": source_kind,
        "source_url": source_url,
    }


def _normalized_item_text(item: dict[str, str], payload: dict[str, Any]) -> str:
    parts = [item["resource_id"], item["source_kind"], item["source_url"]]
    for field in ("source_title", "summary", "content", "body", "text"):
        value = payload.get(field)
        if isinstance(value, str) and value:
            parts.append(value)
    return "\n".join(parts)


def _baseline_index(baseline_path: Path | None) -> dict[str, dict[str, Any]]:
    if baseline_path is None or not baseline_path.exists():
        return {}
    payload = _read_json(baseline_path)
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("baseline items must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for raw in items:
        if isinstance(raw, dict) and isinstance(raw.get("resource_id"), str):
            indexed[raw["resource_id"]] = raw
    return indexed


def _drift_status(
    *,
    snapshot_item: dict[str, Any],
    validated_item: dict[str, str],
    baseline_item: dict[str, Any] | None,
) -> dict[str, Any]:
    content_hash = normalized_hash(_normalized_item_text(validated_item, snapshot_item))
    observed_version = snapshot_item.get("observed_version")
    if observed_version is None:
        observed_version = snapshot_item.get("version")
    license_info = snapshot_item.get("license")
    if license_info is not None and not isinstance(license_info, dict):
        raise ValueError("license must be a mapping when present")

    source_status = str(snapshot_item.get("status") or "").strip().lower()
    if source_status in {"missing", "blocked", "unknown"}:
        drift_status = source_status
        drift_codes = [f"source-{source_status}"]
    elif baseline_item is None:
        drift_status = "missing"
        drift_codes: list[str] = ["missing-baseline"]
    else:
        drift_codes = []
        baseline_hash = baseline_item.get("content_hash")
        baseline_version = baseline_item.get("observed_version")
        baseline_license = baseline_item.get("license")

        if baseline_hash != content_hash:
            drift_codes.append("content_changed")
        if observed_version != baseline_version:
            drift_codes.append("version_changed")
        if license_info != baseline_license:
            drift_codes.append("license_changed")

        if drift_codes:
            drift_status = drift_codes[0]
        else:
            drift_status = "unchanged"

    return {
        "resource_id": validated_item["resource_id"],
        "content_hash": content_hash,
        "observed_version": observed_version,
        "license": license_info,
        "drift": {
            "status": drift_status,
            "codes": drift_codes,
        },
    }


def run_refresh(
    *,
    snapshot_path: Path,
    baseline_path: Path | None = None,
    offline: bool = offline_default,
) -> dict[str, Any]:
    snapshot = _read_json(snapshot_path)
    raw_items = snapshot.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("snapshot items must be a list")
    selection = snapshot.get("selection", {})
    selected_ids = []
    if isinstance(selection, dict):
        for field in ("resource_ids", "agent_resource_ids"):
            maybe_ids = selection.get(field, [])
            if isinstance(maybe_ids, list):
                selected_ids.extend(
                    item
                    for item in maybe_ids
                    if isinstance(item, str) and item not in selected_ids
                )
    selected_set = set(selected_ids)
    baselines = _baseline_index(baseline_path)

    validated_items: list[tuple[int, dict[str, Any], dict[str, str]]] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError("snapshot items must be objects")
        validated = _validate_source(raw)
        if _selected_only_enabled and selected_set and validated["resource_id"] not in selected_set:
            continue
        validated_items.append((index, raw, validated))

    ordered_selection = (
        [entry for entry in selected_ids if any(item[2]["resource_id"] == entry for item in validated_items)]
        if selected_set
        else [item[2]["resource_id"] for item in validated_items]
    )
    by_resource = {item[2]["resource_id"]: item for item in validated_items}
    ordered_items: list[dict[str, Any]] = []
    for resource_id in ordered_selection:
        index, raw, validated = by_resource[resource_id]
        ordered_items.append(
            {
                "resource_id": validated["resource_id"],
                "source_kind": validated["source_kind"],
                "source_url": validated["source_url"],
                **_drift_status(
                    snapshot_item=raw,
                    validated_item=validated,
                    baseline_item=baselines.get(resource_id),
                ),
            }
        )

    return {
        "status": "complete",
        "run_mode": "read_only",
        "selected_only": list(selected_only),
        "offline": offline,
        "network_policy": NETWORK_POLICY,
        "writes": "none",
        "install_policy": INSTALL_POLICY,
        "upgrade_policy": UPGRADE_POLICY,
        "install_or_upgrade": INSTALL_POLICY,
        "items": ordered_items,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh UI resource snapshots without side effects.")
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--offline", action="store_true", default=offline_default)
    args = parser.parse_args(argv)
    result = run_refresh(snapshot_path=args.snapshot, baseline_path=args.baseline, offline=args.offline)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
