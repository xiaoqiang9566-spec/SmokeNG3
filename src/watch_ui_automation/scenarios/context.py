from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

from watch_ui_automation.scenarios.errors import ScenarioVariableError

_REFERENCE_RE = re.compile(r"^\$\{([^}]+)\}$")
_VARIABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_RESERVED_VARIABLES = {"case_id", "baseline", "current_step"}


@dataclass
class ScenarioContext:
    dsl: Any
    session: Any
    case_id: str
    baseline: str
    variables: dict[str, object] = field(default_factory=dict)
    current_step: Any | None = None

    def save_variable(self, name: str, value: object) -> None:
        if not _VARIABLE_NAME_RE.match(name):
            raise ScenarioVariableError(f"Invalid variable name '{name}'")
        if name in _RESERVED_VARIABLES:
            raise ScenarioVariableError(f"Variable '{name}' is reserved")
        if name in self.variables:
            raise ScenarioVariableError(f"Variable '{name}' is already defined")
        self.variables[name] = value

    def resolve_params(self, params: dict[str, object]) -> dict[str, object]:
        return {key: self.resolve_value(value) for key, value in params.items()}

    def resolve_value(self, value: object) -> object:
        if isinstance(value, str):
            match = _REFERENCE_RE.match(value)
            if match:
                return self._resolve_reference(match.group(1))
            return value
        if isinstance(value, list):
            return [self.resolve_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self.resolve_value(item) for key, item in value.items()}
        return value

    def _resolve_reference(self, reference: str) -> object:
        parts = reference.split(".")
        name = parts[0]
        if name in _RESERVED_VARIABLES:
            current: object = getattr(self, name)
        elif name in self.variables:
            current = self.variables[name]
        else:
            raise ScenarioVariableError(f"Unknown variable '{name}'")

        for field_name in parts[1:]:
            current = self._read_field(current, field_name, reference)
        return current

    @staticmethod
    def _read_field(value: object, field_name: str, reference: str) -> object:
        if isinstance(value, dict):
            try:
                return value[field_name]
            except KeyError as error:
                raise ScenarioVariableError(
                    f"Unknown field '{field_name}' in reference '{reference}'"
                ) from error
        if hasattr(value, field_name):
            return getattr(value, field_name)
        raise ScenarioVariableError(
            f"Unknown field '{field_name}' in reference '{reference}'"
        )
