from pathlib import Path

from specify_cli.integrations.base import IntegrationBase


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_template(path: str) -> str:
    template_path = PROJECT_ROOT / path
    raw = template_path.read_text(encoding="utf-8")
    return IntegrationBase.render_template_content(raw, template_path=template_path)
