from __future__ import annotations

from collections.abc import Container
from dataclasses import asdict, is_dataclass

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.errors import ScenarioActionError


def assert_equals(ctx: ScenarioContext, *, actual: object, expected: object) -> None:
    ctx.session.assert_condition(
        ctx.case_id,
        "assert_equals",
        actual == expected,
        actual=artifact_value(actual),
        expected=artifact_value(expected),
        detail="expected values to be equal",
    )


def assert_not_equals(ctx: ScenarioContext, *, actual: object, expected: object) -> None:
    ctx.session.assert_condition(
        ctx.case_id,
        "assert_not_equals",
        actual != expected,
        actual=artifact_value(actual),
        expected={"operator": "!=", "value": artifact_value(expected)},
        detail="expected values to differ",
    )


def assert_non_empty(ctx: ScenarioContext, *, actual: object) -> None:
    condition = bool(str(actual).strip()) if actual is not None else False
    ctx.session.assert_condition(
        ctx.case_id,
        "assert_non_empty",
        condition,
        actual=artifact_value(actual),
        expected="non-empty value",
        detail="expected value to be non-empty",
    )


def assert_changed(ctx: ScenarioContext, *, actual: object, **params: object) -> None:
    if "from" not in params:
        raise ScenarioActionError("assert.changed requires 'from'")
    previous = params.get("from")
    ctx.session.assert_condition(
        ctx.case_id,
        "assert_changed",
        actual != previous,
        actual=artifact_value(actual),
        expected={"operator": "!=", "value": artifact_value(previous)},
        detail="expected value to change",
    )


def assert_contains(ctx: ScenarioContext, *, actual: object, expected: object) -> None:
    if isinstance(actual, str):
        condition = str(expected) in actual
    elif isinstance(actual, Container):
        condition = expected in actual
    else:
        raise ScenarioActionError(
            "assert.contains requires actual to be a string or container"
        )
    ctx.session.assert_condition(
        ctx.case_id,
        "assert_contains",
        condition,
        actual=artifact_value(actual),
        expected={"operator": "contains", "value": artifact_value(expected)},
        detail="expected collection or string to contain value",
    )


def register_assertion_actions(registry: ActionRegistry) -> None:
    registry.register("assert.equals", assert_equals)
    registry.register("assert.not_equals", assert_not_equals)
    registry.register("assert.non_empty", assert_non_empty)
    registry.register("assert.changed", assert_changed)
    registry.register("assert.contains", assert_contains)


def artifact_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [artifact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: artifact_value(item) for key, item in value.items()}
    return value
