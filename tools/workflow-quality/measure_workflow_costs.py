from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


WORD_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")

PROMPT_GLOBS = (
    "templates/commands/*.md",
    "templates/command-partials/**/*.md",
    "templates/passive-skills/**/SKILL.md",
    "templates/worker-prompts/*.md",
)

ARTIFACT_GLOBS = (
    ".specify/discussions/**/*.md",
    ".specify/discussions/**/*.json",
    ".specify/features/**/*.md",
    ".specify/features/**/*.json",
    ".planning/quick/**/*.md",
    ".planning/quick/**/*.json",
)


@dataclass(frozen=True)
class FileMetric:
    path: str
    kind: str
    lines: int
    words: int
    bytes: int


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def count_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def measure_file(root: Path, path: Path, kind: str) -> FileMetric:
    text = path.read_text(encoding="utf-8", errors="replace")
    relative_path = path.relative_to(root).as_posix()
    return FileMetric(
        path=relative_path,
        kind=kind,
        lines=count_lines(text),
        words=count_words(text),
        bytes=len(text.encode("utf-8")),
    )


def iter_matches(root: Path, globs: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def summarize(metrics: list[FileMetric]) -> dict[str, object]:
    totals: dict[str, dict[str, int]] = {}
    for metric in metrics:
        total = totals.setdefault(
            metric.kind,
            {"files": 0, "lines": 0, "words": 0, "bytes": 0},
        )
        total["files"] += 1
        total["lines"] += metric.lines
        total["words"] += metric.words
        total["bytes"] += metric.bytes

    return {
        "totals": totals,
        "files": [asdict(metric) for metric in metrics],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure workflow prompt and artifact cost baselines."
    )
    parser.add_argument("--root", default=".", help="Repository root to measure.")
    parser.add_argument(
        "--include-artifacts",
        action="store_true",
        help="Include generated workflow artifact globs in addition to prompts.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    return parser.parse_args()


def render_markdown(summary: dict[str, object]) -> str:
    totals = summary["totals"]
    if not isinstance(totals, dict):
        raise TypeError("summary['totals'] must be a dictionary")

    lines = [
        "# Workflow Cost Metrics",
        "",
        "## Totals",
        "",
        "| Kind | Files | Lines | Words | Bytes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for kind in sorted(totals):
        total = totals[kind]
        if not isinstance(total, dict):
            raise TypeError("summary['totals'][kind] must be a dictionary")
        lines.append(
            "| {kind} | {files} | {lines} | {words} | {bytes} |".format(
                kind=kind,
                files=total["files"],
                lines=total["lines"],
                words=total["words"],
                bytes=total["bytes"],
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    metrics = [
        measure_file(root, path, "prompt")
        for path in iter_matches(root, PROMPT_GLOBS)
    ]
    if args.include_artifacts:
        metrics.extend(
            measure_file(root, path, "artifact")
            for path in iter_matches(root, ARTIFACT_GLOBS)
        )

    summary = summarize(metrics)
    if args.format == "markdown":
        print(render_markdown(summary), end="")
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
