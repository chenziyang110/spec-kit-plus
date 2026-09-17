"""Read validated JSONL observations and write an offline evaluation report.

No Agent is executed; recorded acceptance is not independently verified here.
Use --strict for auditable identity fields. Existing output is never overwritten.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from quick_adaptive_eval import MODES as MODES, summarize as summarize, validate_record


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def load_records(path: Path, *, strict: bool = False) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line, object_pairs_hook=_object, parse_constant=_nonfinite)
                records.append(validate_record(item, strict=strict))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path.name}:{number}: {exc}") from exc
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Require complete run identity")
    args = parser.parse_args(argv)
    try:
        records = load_records(args.input, strict=args.strict)
        if not records:
            raise ValueError("no observations: empty input is not a benchmark")
        report = summarize(records, strict=args.strict)
        payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
        # Exclusive creation also rejects input/output aliasing and symlinks.
        with args.output.open("x", encoding="utf-8") as destination:
            destination.write(payload)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"quick-eval: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
