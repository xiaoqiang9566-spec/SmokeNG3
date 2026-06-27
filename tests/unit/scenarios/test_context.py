from dataclasses import dataclass

import pytest

from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.errors import ScenarioVariableError


@dataclass(frozen=True)
class CapturedState:
    name: str
    nested: dict[str, object]


def make_context() -> ScenarioContext:
    return ScenarioContext(
        dsl=object(),
        session=object(),
        case_id="case_a",
        baseline="main",
    )


def test_context_resolves_variable_and_field_references() -> None:
    ctx = make_context()
    ctx.save_variable("page", CapturedState(name="main", nested={"path": "root"}))

    assert ctx.resolve_value("${page}") == CapturedState(
        name="main",
        nested={"path": "root"},
    )
    assert ctx.resolve_value("${page.name}") == "main"
    assert ctx.resolve_value("${page.nested.path}") == "root"


def test_context_resolves_nested_params() -> None:
    ctx = make_context()
    ctx.save_variable("page", {"name": "main"})

    assert ctx.resolve_params(
        {
            "actual": "${page.name}",
            "literal": "page",
            "items": ["${page.name}", {"again": "${page.name}"}],
        }
    ) == {
        "actual": "main",
        "literal": "page",
        "items": ["main", {"again": "main"}],
    }


def test_context_rejects_unknown_variable() -> None:
    ctx = make_context()

    with pytest.raises(ScenarioVariableError, match="Unknown variable"):
        ctx.resolve_value("${missing}")


def test_context_rejects_duplicate_and_reserved_variable_names() -> None:
    ctx = make_context()
    ctx.save_variable("value", 1)

    with pytest.raises(ScenarioVariableError, match="already defined"):
        ctx.save_variable("value", 2)

    with pytest.raises(ScenarioVariableError, match="reserved"):
        ctx.save_variable("case_id", "bad")
