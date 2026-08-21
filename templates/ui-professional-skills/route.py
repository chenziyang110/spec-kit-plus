from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _signal_matches(
    query: str, skill: dict[str, Any]
) -> tuple[list[str], list[str]]:
    triggers = skill.get("triggers", {})
    phrases = triggers.get("phrases", [])
    negatives = triggers.get("negative_phrases", [])
    matched = [phrase for phrase in phrases if _normalized(phrase) in query]
    blocked = [phrase for phrase in negatives if _normalized(phrase) in query]
    return matched, blocked


def _score(query: str, skill: dict[str, Any]) -> tuple[int, list[str]]:
    matched, blocked = _signal_matches(query, skill)
    return len(matched) - (2 * len(blocked)), matched


def _rank(
    query: str, skills: list[dict[str, Any]], kind: str
) -> list[tuple[int, int, dict[str, Any], list[str]]]:
    ranked: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, skill in enumerate(skills):
        if skill.get("kind") != kind:
            continue
        score, matched = _score(query, skill)
        if score > 0:
            ranked.append((score, -index, skill, matched))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked


def _empty_asset_inventory(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "manifest_refs": [],
        "lockfile_refs": [],
        "framework_ids": [],
        "installed_resources": [],
        "component_roots": [],
        "token_refs": [],
        "theme_refs": [],
        "surface_refs": [],
    }


def _existing_refs(project_root: Path, candidates: Any) -> list[str]:
    if not isinstance(candidates, list):
        return []
    refs: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_absolute():
            continue
        try:
            resolved = (project_root / candidate_path).resolve()
            relative = resolved.relative_to(project_root)
        except (OSError, RuntimeError, ValueError):
            # Catalog overrides are inputs too. Never let an asset marker
            # escape the explicitly selected project root, including through
            # `..` segments or symlinks.
            continue
        ref = relative.as_posix()
        if resolved.exists() and ref not in refs:
            refs.append(ref)
    return refs


def _most_specific_refs(refs: list[str]) -> list[str]:
    return [
        ref
        for ref in refs
        if not any(
            other != ref and Path(other).is_relative_to(Path(ref))
            for other in refs
        )
    ]


def _dependency_version(
    dependencies: dict[str, str], markers: Any
) -> str | None:
    if not isinstance(markers, list):
        return None
    dependency_names = sorted(dependencies)
    for marker in markers:
        if not isinstance(marker, str) or not marker:
            continue
        if marker.endswith("/"):
            matches = [name for name in dependency_names if name.startswith(marker)]
            if matches:
                return dependencies[matches[0]]
        elif marker in dependencies:
            return dependencies[marker]
    return None


def scan_web_ui_assets(
    project_root: Path | None, catalog: dict[str, Any]
) -> dict[str, Any]:
    if project_root is None:
        return _empty_asset_inventory("not-scanned")
    try:
        root = project_root.resolve()
    except OSError:
        return _empty_asset_inventory("unavailable")
    if not root.is_dir():
        return _empty_asset_inventory("unavailable")

    routing = catalog.get("mature_web_ui_routing", {})
    scan = routing.get("asset_scan", {}) if isinstance(routing, dict) else {}
    inventory = _empty_asset_inventory("scanned")
    inventory["manifest_refs"] = _existing_refs(root, scan.get("manifest_files"))
    inventory["lockfile_refs"] = _existing_refs(root, scan.get("lockfile_files"))
    inventory["component_roots"] = _most_specific_refs(
        _existing_refs(root, scan.get("component_roots"))
    )
    inventory["token_refs"] = _existing_refs(root, scan.get("token_files"))
    inventory["theme_refs"] = _existing_refs(root, scan.get("theme_files"))
    inventory["surface_refs"] = _existing_refs(root, scan.get("surface_files"))

    dependencies: dict[str, str] = {}
    for manifest_ref in inventory["manifest_refs"]:
        try:
            manifest = json.loads((root / manifest_ref).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            inventory["status"] = "partial"
            continue
        if not isinstance(manifest, dict):
            inventory["status"] = "partial"
            continue
        for group in (
            "dependencies",
            "devDependencies",
            "peerDependencies",
            "optionalDependencies",
        ):
            raw_dependencies = manifest.get(group, {})
            if not isinstance(raw_dependencies, dict):
                continue
            for name, version in raw_dependencies.items():
                if isinstance(name, str) and isinstance(version, str):
                    dependencies.setdefault(name, version)

    framework_markers = routing.get("framework_package_markers", {})
    if isinstance(framework_markers, dict):
        inventory["framework_ids"] = [
            framework
            for framework, markers in framework_markers.items()
            if isinstance(framework, str)
            and _dependency_version(dependencies, markers) is not None
        ]

    package_markers = routing.get("resource_package_markers", {})
    file_markers = routing.get("resource_file_markers", {})
    package_markers = package_markers if isinstance(package_markers, dict) else {}
    file_markers = file_markers if isinstance(file_markers, dict) else {}
    installed_resources: list[dict[str, str]] = []
    for resource in catalog.get("mature_web_ui_resources", []):
        if not isinstance(resource, dict) or resource.get("category") == "agent-resource":
            continue
        resource_id = resource.get("id")
        if not isinstance(resource_id, str):
            continue
        version = _dependency_version(dependencies, package_markers.get(resource_id))
        if version is None and _existing_refs(root, file_markers.get(resource_id)):
            version = "local-source"
        if version is not None:
            installed_resources.append(
                {"resource_id": resource_id, "version": version}
            )
    inventory["installed_resources"] = installed_resources
    return inventory


def _web_ui_signals(
    catalog: dict[str, Any],
    query: str,
    inventory: dict[str, Any] | None = None,
) -> tuple[bool, set[str], set[str]]:
    routing = catalog.get("mature_web_ui_routing", {})
    if not isinstance(routing, dict):
        return False, set(), set()
    framework_signals = routing.get("framework_signals", {})
    framework_signals = framework_signals if isinstance(framework_signals, dict) else {}
    matched_frameworks = {
        framework
        for framework, signals in framework_signals.items()
        if isinstance(framework, str)
        and isinstance(signals, list)
        and any(
            isinstance(signal, str) and _normalized(signal) in query
            for signal in signals
        )
    }
    if isinstance(inventory, dict):
        matched_frameworks.update(
            framework
            for framework in inventory.get("framework_ids", [])
            if isinstance(framework, str) and framework in framework_signals
        )
    activation_signals = routing.get("activation_signals", [])
    has_explicit_web_signal = isinstance(activation_signals, list) and any(
        isinstance(signal, str) and _normalized(signal) in query
        for signal in activation_signals
    )
    non_web_platform_signals = routing.get("non_web_platform_signals", [])
    has_non_web_platform_signal = isinstance(non_web_platform_signals, list) and any(
        isinstance(signal, str) and _normalized(signal) in query
        for signal in non_web_platform_signals
    )
    is_web_ui = bool(matched_frameworks) or has_explicit_web_signal
    if has_non_web_platform_signal and not has_explicit_web_signal:
        is_web_ui = False

    capability_signals = routing.get("capability_signals", {})
    capability_signals = capability_signals if isinstance(capability_signals, dict) else {}
    matched_capabilities = {
        capability
        for capability, signals in capability_signals.items()
        if isinstance(capability, str)
        and isinstance(signals, list)
        and any(
            isinstance(signal, str) and _normalized(signal) in query
            for signal in signals
        )
    }
    return is_web_ui, matched_frameworks, matched_capabilities


def _resource_matches_ecosystem(
    resource: dict[str, Any],
    matched_frameworks: set[str],
    default_resource_ids: set[str],
) -> bool:
    ecosystems = set(resource.get("ecosystems", []))
    if matched_frameworks:
        return bool(ecosystems.intersection(matched_frameworks)) or (
            "framework-agnostic" in ecosystems
        )
    if "general" not in resource.get("capabilities", []):
        return "framework-agnostic" in ecosystems
    return resource.get("id") in default_resource_ids


def _mature_web_ui_resource_ids(
    catalog: dict[str, Any],
    query: str,
    inventory: dict[str, Any] | None = None,
) -> list[str]:
    routing = catalog.get("mature_web_ui_routing", {})
    resources = catalog.get("mature_web_ui_resources", [])
    if not isinstance(routing, dict) or not isinstance(resources, list):
        return []
    is_web_ui, matched_frameworks, matched_capabilities = _web_ui_signals(
        catalog, query, inventory
    )
    if not is_web_ui:
        return []

    by_id = {
        resource["id"]: resource
        for resource in resources
        if isinstance(resource, dict) and isinstance(resource.get("id"), str)
    }
    primary_limit = int(routing.get("primary_limit", 8))
    agent_limit = int(routing.get("agent_limit", 4))
    shortlist_limit = int(routing.get("shortlist_limit", 16))
    default_resource_ids = set(routing.get("default_resource_ids", []))

    primary_ids: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("category") == "agent-resource":
            continue
        if "general" not in resource.get("capabilities", []):
            continue
        if _resource_matches_ecosystem(
            resource, matched_frameworks, default_resource_ids
        ):
            primary_ids.append(resource["id"])
        if len(primary_ids) >= primary_limit:
            break

    specialist_ids: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("category") == "agent-resource":
            continue
        capabilities = set(resource.get("capabilities", []))
        if "general" in capabilities or not capabilities.intersection(matched_capabilities):
            continue
        if (
            _resource_matches_ecosystem(
                resource, matched_frameworks, default_resource_ids
            )
            and resource["id"] not in primary_ids
        ):
            specialist_ids.append(resource["id"])

    agent_ids: list[str] = []
    for resource_id in [*primary_ids, *specialist_ids]:
        for agent_id in by_id.get(resource_id, {}).get("agent_resource_ids", []):
            if agent_id in by_id and agent_id not in agent_ids:
                agent_ids.append(agent_id)
            if len(agent_ids) >= agent_limit:
                break
        if len(agent_ids) >= agent_limit:
            break

    shortlist: list[str] = []
    for resource_id in [*primary_ids, *specialist_ids, *agent_ids]:
        if resource_id not in shortlist:
            shortlist.append(resource_id)
    return shortlist[:shortlist_limit]


def _resource_score(
    resource: dict[str, Any],
    *,
    matched_frameworks: set[str],
    matched_capabilities: set[str],
    installed_resource_ids: set[str],
    routing: dict[str, Any],
) -> tuple[int, list[str]]:
    scoring = routing.get("selection_scoring", {})
    scoring = scoring if isinstance(scoring, dict) else {}
    maturity_scores = scoring.get("maturity", {})
    maturity_scores = maturity_scores if isinstance(maturity_scores, dict) else {}
    resource_id = str(resource.get("id") or "")
    ecosystems = set(resource.get("ecosystems", []))
    capabilities = set(resource.get("capabilities", []))
    score = 0
    reason_codes: list[str] = []

    if resource_id in installed_resource_ids:
        score += int(scoring.get("installed", 0))
        reason_codes.append("installed")
    ecosystem_matches = sorted(ecosystems.intersection(matched_frameworks))
    if ecosystem_matches:
        score += int(scoring.get("ecosystem", 0))
        reason_codes.append(f"ecosystem:{ecosystem_matches[0]}")
    elif "framework-agnostic" in ecosystems:
        score += int(scoring.get("framework_agnostic", 0))
        reason_codes.append("ecosystem:framework-agnostic")

    capability_matches = [
        capability
        for capability in routing.get("capability_signals", {})
        if capability in capabilities and capability in matched_capabilities
    ]
    if capability_matches:
        score += int(scoring.get("capability", 0)) * len(capability_matches)
        reason_codes.extend(
            f"capability:{capability}" for capability in capability_matches
        )
    if "general" in capabilities:
        score += int(scoring.get("general", 0))
        reason_codes.append("capability:general")
    maturity = str(resource.get("maturity") or "")
    score += int(maturity_scores.get(maturity, 0))
    if maturity:
        reason_codes.append(f"maturity:{maturity}")
    if resource.get("agent_resource_ids"):
        score += int(scoring.get("official_agent_material", 0))
        reason_codes.append("official-agent-material")
    if resource_id in set(routing.get("default_resource_ids", [])):
        score += int(scoring.get("default_resource", 0))
        reason_codes.append("default-resource")
    return score, reason_codes[:6]


def _select_mature_web_ui_resources(
    catalog: dict[str, Any],
    *,
    is_web_ui: bool,
    matched_frameworks: set[str],
    matched_capabilities: set[str],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    if not is_web_ui:
        return {
            "status": "not-applicable",
            "primary_resource_id": None,
            "supporting_resource_ids": [],
            "agent_resource_ids": [],
            "candidates": [],
            "confirmation_codes": [],
        }
    routing = catalog.get("mature_web_ui_routing", {})
    resources = catalog.get("mature_web_ui_resources", [])
    if not isinstance(routing, dict) or not isinstance(resources, list):
        return {
            "status": "unresolved",
            "primary_resource_id": None,
            "supporting_resource_ids": [],
            "agent_resource_ids": [],
            "candidates": [],
            "confirmation_codes": ["catalog-unavailable"],
        }

    installed_resource_ids = {
        item.get("resource_id")
        for item in inventory.get("installed_resources", [])
        if isinstance(item, dict) and isinstance(item.get("resource_id"), str)
    }
    defaults = set(routing.get("default_resource_ids", []))
    ranked: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict) or resource.get("category") == "agent-resource":
            continue
        if not _resource_matches_ecosystem(resource, matched_frameworks, defaults):
            continue
        score, reasons = _resource_score(
            resource,
            matched_frameworks=matched_frameworks,
            matched_capabilities=matched_capabilities,
            installed_resource_ids=installed_resource_ids,
            routing=routing,
        )
        ranked.append((score, -index, resource, reasons))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

    primary_ranked = [
        item
        for item in ranked
        if item[2].get("category") in {"component-library", "design-system"}
        and "general" in item[2].get("capabilities", [])
    ]
    primary = primary_ranked[0] if primary_ranked else None
    primary_id = primary[2]["id"] if primary else None

    supporting: list[tuple[int, int, dict[str, Any], list[str]]] = []
    headless_selected = False
    capability_order = [
        capability
        for capability in routing.get("capability_signals", {})
        if capability in matched_capabilities
    ]
    for capability in capability_order:
        candidates = []
        for item in ranked:
            resource = item[2]
            capabilities = set(resource.get("capabilities", []))
            if resource.get("id") == primary_id or capability not in capabilities:
                continue
            is_headless = resource.get("category") == "headless-primitive"
            is_specialist = "general" not in capabilities
            if not is_headless and not is_specialist:
                continue
            if is_headless and headless_selected:
                continue
            candidates.append(item)
        if not candidates:
            continue
        selected = candidates[0]
        if selected not in supporting:
            supporting.append(selected)
            if selected[2].get("category") == "headless-primitive":
                headless_selected = True
        if len(supporting) >= 3:
            break

    selected_items = ([primary] if primary is not None else []) + supporting
    candidates_payload = [
        {
            "resource_id": item[2]["id"],
            "role": (
                "primary"
                if item is primary
                else (
                    "headless"
                    if item[2].get("category") == "headless-primitive"
                    else "specialist"
                )
            ),
            "score": item[0],
            "reason_codes": item[3],
        }
        for item in selected_items
    ]
    agent_resource_ids: list[str] = []
    for item in selected_items:
        for agent_id in item[2].get("agent_resource_ids", []):
            if isinstance(agent_id, str) and agent_id not in agent_resource_ids:
                agent_resource_ids.append(agent_id)
    agent_resource_ids = agent_resource_ids[: int(routing.get("agent_limit", 4))]

    confirmation_codes: list[str] = []
    inventory_status = inventory.get("status")
    if inventory_status == "not-scanned":
        confirmation_codes.append("asset-inventory-not-scanned")
    elif inventory_status != "scanned":
        confirmation_codes.append("asset-inventory-incomplete")
    installed_primary_ids = [
        item[2]["id"]
        for item in primary_ranked
        if item[2]["id"] in installed_resource_ids
    ]
    if len(installed_primary_ids) > 1:
        confirmation_codes.append("multiple-installed-primary-systems")
    if (
        inventory_status == "scanned"
        and inventory.get("component_roots")
        and not installed_resource_ids
    ):
        confirmation_codes.append("live-components-unmapped")
    if primary is None:
        confirmation_codes.append("no-compatible-primary-system")

    if primary is None:
        status = "unresolved"
    elif inventory_status == "scanned" and not confirmation_codes:
        status = "resolved"
    else:
        status = "provisional"
    return {
        "status": status,
        "primary_resource_id": primary_id,
        "supporting_resource_ids": [item[2]["id"] for item in supporting],
        "agent_resource_ids": agent_resource_ids,
        "candidates": candidates_payload,
        "confirmation_codes": confirmation_codes,
    }


def _smoothness_acceptance_ids(
    catalog: dict[str, Any],
    *,
    is_web_ui: bool,
    matched_capabilities: set[str],
) -> list[str]:
    if not is_web_ui:
        return []
    routing = catalog.get("mature_web_ui_routing", {})
    checks = routing.get("smoothness_acceptance_checks", []) if isinstance(routing, dict) else []
    accepted: list[str] = []
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("id"), str):
            continue
        capabilities = check.get("capabilities", [])
        if not isinstance(capabilities, list):
            continue
        if not capabilities or set(capabilities).intersection(matched_capabilities):
            accepted.append(check["id"])
    return accepted


def route(
    catalog: dict[str, Any],
    raw_query: str,
    *,
    style_authority: str = "greenfield",
    project_root: Path | None = None,
) -> dict[str, Any]:
    query = _normalized(raw_query)
    skills = catalog["skills"]
    routing = catalog["routing"]
    by_id = {skill["id"]: skill for skill in skills}
    matched_signals: dict[str, list[str]] = {}
    ambiguities: list[dict[str, Any]] = []

    domains = _rank(query, skills, "domain")
    if not domains:
        domain_id = routing["fallback_domain"]
    else:
        domain_id = domains[0][2]["id"]
        matched_signals[domain_id] = domains[0][3]
        tied = [item[2]["id"] for item in domains if item[0] == domains[0][0]]
        if len(tied) > 1:
            ambiguities.append({"kind": "domain", "candidate_ids": tied})
            domain_id = routing["fallback_domain"]

    style_id: str | None = None
    if style_authority != "inherit-existing":
        direct_style_signals = []
        for skill in skills:
            if skill.get("kind") != "style":
                continue
            matched, blocked = _signal_matches(query, skill)
            if matched:
                direct_style_signals.append((skill, matched, blocked))

        explicit_style_conflict = (
            len(direct_style_signals) > 1
            and any(blocked for _, _, blocked in direct_style_signals)
        )
        styles = _rank(query, skills, "style")
        if explicit_style_conflict:
            candidate_ids = [skill["id"] for skill, _, _ in direct_style_signals]
            ambiguities.append({"kind": "style", "candidate_ids": candidate_ids})
            for skill, matched, _ in direct_style_signals:
                matched_signals[skill["id"]] = matched
        elif styles:
            top_score = styles[0][0]
            tied = [item for item in styles if item[0] == top_score]
            if len(tied) > 1:
                ambiguities.append(
                    {
                        "kind": "style",
                        "candidate_ids": [item[2]["id"] for item in tied],
                    }
                )
                for _, _, skill, matched in tied:
                    matched_signals[skill["id"]] = matched
            else:
                style_id = styles[0][2]["id"]
                matched_signals[style_id] = styles[0][3]

    specialist_limit = int(routing["specialist_limit"])
    specialist_ids: list[str] = []
    for _, _, skill, matched in _rank(query, skills, "specialist")[:specialist_limit]:
        specialist_ids.append(skill["id"])
        matched_signals[skill["id"]] = matched

    question_required = bool(ambiguities)
    if question_required:
        # A material route conflict pauses specialist/style loading. The one
        # stable domain is enough context to ask the next direction-changing
        # question without contaminating the round with competing references.
        style_id = None
        specialist_ids = []

    selected_ids = [domain_id]
    if style_id is not None:
        selected_ids.append(style_id)
    selected_ids.extend(specialist_ids)
    load_refs = [by_id[skill_id]["ref"] for skill_id in selected_ids]
    asset_inventory = scan_web_ui_assets(project_root, catalog)
    is_web_ui, web_frameworks, web_capabilities = _web_ui_signals(
        catalog, query, asset_inventory
    )
    mature_resource_ids = _mature_web_ui_resource_ids(
        catalog, query, asset_inventory
    )
    mature_selection = _select_mature_web_ui_resources(
        catalog,
        is_web_ui=is_web_ui,
        matched_frameworks=web_frameworks,
        matched_capabilities=web_capabilities,
        inventory=asset_inventory,
    )
    smoothness_ids = _smoothness_acceptance_ids(
        catalog,
        is_web_ui=is_web_ui,
        matched_capabilities=web_capabilities,
    )

    question = None
    if ambiguities:
        candidate_names = [
            by_id[skill_id]["name"]
            for ambiguity in ambiguities
            for skill_id in ambiguity["candidate_ids"]
        ]
        question = (
            "这轮最应该优先保留哪一种方向："
            + "、".join(candidate_names)
            + "？"
        )

    unresolved_candidates = [
        skill_id
        for ambiguity in ambiguities
        for skill_id in ambiguity["candidate_ids"]
    ]
    professional_skill_route = {
        "catalog_version": catalog["catalog_id"],
        "status": "question-required" if question_required else "resolved",
        "domain_skill_id": domain_id,
        "style_skill_id": style_id,
        "specialist_skill_ids": specialist_ids,
        "matched_signals": matched_signals,
        "loaded_refs": load_refs,
        "unresolved_candidates": unresolved_candidates,
        "mature_web_ui_resource_ids": mature_resource_ids,
        "web_ui_asset_inventory": asset_inventory,
        "mature_web_ui_selection": mature_selection,
        "smoothness_acceptance_ids": smoothness_ids,
    }

    return {
        "catalog_id": catalog["catalog_id"],
        "style_authority": style_authority,
        "selection": {
            "domain_skill_id": domain_id,
            "style_skill_id": style_id,
            "specialist_skill_ids": specialist_ids,
        },
        "matched_signals": matched_signals,
        "ambiguities": ambiguities,
        "question_required": question_required,
        "question": question,
        "load_refs": load_refs,
        "mature_web_ui_resource_ids": mature_resource_ids,
        "web_ui_asset_inventory": asset_inventory,
        "mature_web_ui_selection": mature_selection,
        "smoothness_acceptance_ids": smoothness_ids,
        "professional_skill_route": professional_skill_route,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Route one UI request sparsely.")
    parser.add_argument("--query", required=True)
    parser.add_argument(
        "--style-authority",
        choices=("greenfield", "inherit-existing", "page-overhaul-authorized"),
        default="greenfield",
        help="Whether a routed style may influence this exact design scope.",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).with_name("catalog.json"),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Read only known local UI manifests and paths for asset-aware selection.",
    )
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    print(
        json.dumps(
            route(
                catalog,
                args.query,
                style_authority=args.style_authority,
                project_root=args.project_root,
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
