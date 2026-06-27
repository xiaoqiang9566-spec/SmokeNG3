from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.errors import ScenarioSchemaError
from watch_ui_automation.scenarios.models import ScenarioCase, ScenarioStep

ALLOWED_MARKERS = {"yaml", "device", "smoke", "regression", "stability"}
TOP_LEVEL_FIELDS = {"cases"}
CASE_FIELDS = {"id", "title", "markers", "baseline", "steps"}
STEP_FIELDS = {"name", "action", "params", "save_as"}
BUILTIN_VARIABLES = {"case_id", "baseline", "current_step"}
VARIABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
REFERENCE_RE = re.compile(r"\$\{([^}]+)\}")
FULL_REFERENCE_RE = re.compile(r"^\$\{([^}]+)\}$")


def parse_cases(
    payload: object,
    *,
    source_file: str,
    registry: ActionRegistry,
) -> list[ScenarioCase]:
    if not isinstance(payload, dict):
        raise ScenarioSchemaError(f"YAML top-level must be an object in {source_file}")
    _reject_unknown_fields(payload, TOP_LEVEL_FIELDS, source_file=source_file)

    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ScenarioSchemaError(f"'cases' must be a non-empty list in {source_file}")

    cases: list[ScenarioCase] = []
    seen_ids: set[str] = set()
    for raw_case in raw_cases:
        case = _parse_case(raw_case, source_file=source_file, registry=registry)
        if case.id in seen_ids:
            raise ScenarioSchemaError(f"Duplicate case id '{case.id}' in {source_file}")
        seen_ids.add(case.id)
        cases.append(case)
    return cases


def _parse_case(
    raw_case: object,
    *,
    source_file: str,
    registry: ActionRegistry,
) -> ScenarioCase:
    if not isinstance(raw_case, dict):
        raise ScenarioSchemaError(f"Each case must be an object in {source_file}")

    case_id = _required_str(raw_case, "id", source_file)
    if not VARIABLE_NAME_RE.match(case_id):
        raise ScenarioSchemaError(f"Invalid case id '{case_id}' in {source_file}")
    _reject_unknown_fields(
        raw_case,
        CASE_FIELDS,
        source_file=source_file,
        case_id=case_id,
    )

    title = _required_str(raw_case, "title", source_file)
    baseline = _required_str(raw_case, "baseline", source_file)
    markers = _parse_markers(raw_case.get("markers"), source_file)
    raw_steps = raw_case.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ScenarioSchemaError(f"'steps' must be a non-empty list in {source_file}")

    defined_variables = set(BUILTIN_VARIABLES)
    saved_variables: set[str] = set()
    steps: list[ScenarioStep] = []
    for raw_step in raw_steps:
        step = _parse_step(
            raw_step,
            source_file=source_file,
            case_id=case_id,
            registry=registry,
        )
        _validate_references(
            step.params,
            defined_variables=defined_variables,
            source_file=source_file,
            case_id=case_id,
            step_name=step.name,
        )
        if step.save_as:
            if step.save_as in saved_variables:
                raise ScenarioSchemaError(
                    f"Duplicate save_as '{step.save_as}' in {source_file}, case={case_id}"
                )
            saved_variables.add(step.save_as)
            defined_variables.add(step.save_as)
        steps.append(step)

    return ScenarioCase(
        id=case_id,
        title=title,
        markers=markers,
        baseline=baseline,
        steps=steps,
        source_file=source_file,
    )


def _parse_step(
    raw_step: object,
    *,
    source_file: str,
    case_id: str,
    registry: ActionRegistry,
) -> ScenarioStep:
    if not isinstance(raw_step, dict):
        raise ScenarioSchemaError(f"Each step must be an object in {source_file}")

    name = _required_str(raw_step, "name", source_file)
    _reject_unknown_fields(
        raw_step,
        STEP_FIELDS,
        source_file=source_file,
        case_id=case_id,
        step_name=name,
    )
    action = _required_str(raw_step, "action", source_file)
    if action not in registry:
        raise ScenarioSchemaError(
            f"Unknown action '{action}' in {source_file}, case={case_id}, step={name}"
        )

    params = raw_step.get("params", {})
    if not isinstance(params, dict):
        raise ScenarioSchemaError(f"'params' must be an object in {source_file}")

    save_as = raw_step.get("save_as")
    if save_as is not None:
        if not isinstance(save_as, str) or not VARIABLE_NAME_RE.match(save_as):
            raise ScenarioSchemaError(f"Invalid save_as '{save_as}' in {source_file}")
        if save_as in BUILTIN_VARIABLES:
            raise ScenarioSchemaError(f"save_as '{save_as}' is reserved in {source_file}")

    return ScenarioStep(name=name, action=action, params=params, save_as=save_as)


def _reject_unknown_fields(
    raw: dict[object, object],
    allowed_fields: set[str],
    *,
    source_file: str,
    case_id: str | None = None,
    step_name: str | None = None,
) -> None:
    unknown_fields = sorted(key for key in raw if key not in allowed_fields)
    if not unknown_fields:
        return

    parts = [f"Unknown field {unknown_fields[0]!r} in {source_file}"]
    if case_id is not None:
        parts.append(f"case={case_id}")
    if step_name is not None:
        parts.append(f"step={step_name}")
    raise ScenarioSchemaError(", ".join(parts))


def _required_str(raw: dict[str, object], key: str, source_file: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ScenarioSchemaError(f"'{key}' must be a non-empty string in {source_file}")
    return value


def _parse_markers(raw_markers: object, source_file: str) -> list[str]:
    if not isinstance(raw_markers, list) or not all(
        isinstance(marker, str) for marker in raw_markers
    ):
        raise ScenarioSchemaError(f"'markers' must be a string list in {source_file}")
    for marker in raw_markers:
        if marker not in ALLOWED_MARKERS:
            raise ScenarioSchemaError(f"Unknown marker '{marker}' in {source_file}")
    return list(raw_markers)


def _validate_references(
    value: object,
    *,
    defined_variables: set[str],
    source_file: str,
    case_id: str,
    step_name: str,
) -> None:
    for reference in _iter_references(value):
        _validate_reference_syntax(reference, source_file=source_file)
        variable_name = reference.split(".")[0]
        if variable_name not in defined_variables:
            raise ScenarioSchemaError(
                f"Undefined variable '{variable_name}' in {source_file}, "
                f"case={case_id}, step={step_name}"
            )


def _validate_reference_syntax(reference: str, *, source_file: str) -> None:
    parts = reference.split(".")
    if not parts or not all(VARIABLE_NAME_RE.match(part) for part in parts):
        raise ScenarioSchemaError(
            f"Invalid variable reference '{reference}' in {source_file}"
        )


def _iter_references(value: object) -> Iterable[str]:
    if isinstance(value, str):
        if "${" in value or "}" in value:
            match = FULL_REFERENCE_RE.match(value)
            if not match:
                if "${" in value and "}" in value:
                    raise ScenarioSchemaError(
                        f"Variable reference must occupy the full string: {value!r}"
                    )
                raise ScenarioSchemaError(
                    f"Invalid variable reference syntax: {value!r}"
                )
            yield match.group(1)
            return
        for match in REFERENCE_RE.finditer(value):
            yield match.group(1)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_references(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_references(item)
