#!/usr/bin/env python3
"""Compose the self-contained design preview from small Jinja source parts.

The checked-in HTML file is a compatibility artifact for integrations and tests.
Edit ``templates/design-preview/**`` and run this script; use ``--check`` in CI.
``--bootstrap-parts`` exists only to deterministically split the legacy monolith.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = REPO_ROOT / "src" / "specify_cli" / "design_preview_source"
DEFAULT_OUTPUT = REPO_ROOT / "templates" / "design-preview-template.html"
STYLE_OPEN = "  <style>\n"
STYLE_CLOSE = "  </style>\n"
BODY_OPEN = "<body"
MANIFEST_OPEN = '  <script type="application/json" id="design-preview-manifest">\n'
RUNTIME_OPEN = "  </script>\n\n  <script>\n"
RUNTIME_CLOSE = "  </script>\n</body>\n</html>\n"
CSS_LAYERS = ("reset", "tokens", "base", "layout", "components", "motion", "responsive")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def bootstrap_parts(source: Path, template_dir: Path) -> None:
    """Split the legacy compatibility HTML without changing one rendered byte."""

    content = source.read_text(encoding="utf-8")
    style_open = content.index(STYLE_OPEN) + len(STYLE_OPEN)
    style_close = content.index(STYLE_CLOSE, style_open)
    body_open = content.index(BODY_OPEN, style_close)
    manifest_open = content.index(MANIFEST_OPEN, body_open) + len(MANIFEST_OPEN)
    runtime_open = content.index(RUNTIME_OPEN, manifest_open)
    runtime_content = runtime_open + len(RUNTIME_OPEN)
    runtime_close = content.rindex(RUNTIME_CLOSE)

    styles = content[style_open:style_close]
    layer_offsets = [styles.index(f"    @layer {name} {{") for name in CSS_LAYERS]
    style_parts: list[tuple[str, str]] = [
        ("00-preamble.css", styles[: layer_offsets[0]])
    ]
    for index, name in enumerate(CSS_LAYERS):
        start = layer_offsets[index]
        end = layer_offsets[index + 1] if index + 1 < len(layer_offsets) else len(styles)
        style_parts.append((f"{index + 1:02d}-{name}.css", styles[start:end]))
    for name, part in style_parts:
        _write(template_dir / "styles" / name, part)

    style_includes = "".join(
        f'{{% include "styles/{name}" %}}\n' for name, _ in style_parts
    )
    _write(template_dir / "styles.css.j2", style_includes)

    shell = (
        content[:style_open]
        + '{% include "styles.css.j2" %}\n'
        + content[style_close:body_open]
        + '{% include "review-board.html.j2" %}\n'
    )
    _write(template_dir / "template.html.j2", shell)

    review_board = (
        content[body_open:manifest_open]
        + '{% include "manifest.json" %}\n'
        + content[runtime_open:runtime_content]
        + '{% include "runtime.js" %}\n'
        + content[runtime_close:]
    )
    _write(template_dir / "review-board.html.j2", review_board)
    _write(template_dir / "manifest.json", content[manifest_open:runtime_open])
    _write(template_dir / "runtime.js", content[runtime_content:runtime_close])


def render(template_dir: Path) -> str:
    environment = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        newline_sequence="\n",
    )
    return environment.get_template("template.html.j2").render()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bootstrap-parts", action="store_true")
    args = parser.parse_args()

    if args.bootstrap_parts:
        bootstrap_parts(args.out, args.template_dir)

    rendered = render(args.template_dir)
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.is_file() else ""
        if current != rendered:
            print(f"stale generated design preview: {args.out}")
            return 1
        print(f"design preview is synchronized: {args.out}")
        return 0

    _write(args.out, rendered)
    print(f"rendered design preview: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
