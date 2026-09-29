_FALLBACK_CORE_COMMAND_NAMES = frozenset({
    "analyze",
    "checklist",
    "constitution",
    "debug",
    "deep-research",
    "discussion",
    "explain",
    "implement",
    "map-scan",
    "map-build",
    "plan",
    "specify",
    "team",
    "tasks",
    "taskstoissues",
    "test-design",
})
EXTENSION_COMMAND_NAME_PATTERN = re.compile(r"^sp\.([a-z0-9-]+)\.([a-z0-9-]+)$")
