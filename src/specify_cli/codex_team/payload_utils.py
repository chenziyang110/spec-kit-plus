"""Helpers for building/reading schema-backed payloads."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Type


def filter_payload(payload: dict[str, Any], dataclass_type: Type[Any]) -> dict[str, Any]:
    allowed = {field.name for field in fields(dataclass_type)}
    return {key: value for key, value in payload.items() if key in allowed}
