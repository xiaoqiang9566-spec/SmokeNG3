from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def load_case_data(path: str | Path) -> list[dict[str, Any]]:
    payload = load_yaml(path)
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError(f"cases must be a list: {path}")
    return cases
