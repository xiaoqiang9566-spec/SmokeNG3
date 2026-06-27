from __future__ import annotations

import pytest

from watch_ui_automation.actions import create_default_registry
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.errors import ScenarioActionError
from watch_ui_automation.scenarios.models import PageState, WidgetState, WorkoutState


class FakeSession:
    def __init__(self) -> None:
        self.assertions = []
        self.steps = []
        self.current_page = "main"

    def read_json(self, uri: str):
        return {"Content": self.current_page}

    def record_step(self, case_name: str, name: str, status: str, **extra) -> None:
        self.steps.append((case_name, name, status, extra))

    def assert_condition(
        self,
        case_name: str,
        name: str,
        condition: bool,
        *,
        actual: object,
        expected: object,
        detail: str | None = None,
    ) -> None:
        self.assertions.append((case_name, name, condition, actual, expected, detail))
        if not condition:
            raise AssertionError(detail or name)


class FakeWatchface:
    def __init__(self) -> None:
        self.calls = []

    def open_widget(self, case_name: str) -> None:
        self.calls.append(("open_widget", case_name))

    def open_workout(self, case_name: str) -> None:
        self.calls.append(("open_workout", case_name))


class FakeWidget:
    def __init__(self) -> None:
        self.name = "/_watch-face(c)/main"
        self.calls = []

    def current_name(self) -> str:
        return self.name

    def go_back(self, case_name: str) -> None:
        self.calls.append(("go_back", case_name))


class FakeWorkout:
    def __init__(self) -> None:
        self.state_value = "ready"
        self.calls = []

    def state(self) -> str:
        return self.state_value

    def pause_or_resume(self, case_name: str) -> None:
        self.calls.append(("pause_or_resume", case_name))

    def stop(self, case_name: str) -> None:
        self.calls.append(("stop", case_name))


class FakeDsl:
    def __init__(self) -> None:
        self.session = FakeSession()
        self.resources = {"current_page": "page://current"}
        self.watchface = FakeWatchface()
        self.widget = FakeWidget()
        self.workout = FakeWorkout()


def make_context() -> ScenarioContext:
    dsl = FakeDsl()
    dsl.session.current_page = "main"
    return ScenarioContext(
        dsl=dsl,
        session=dsl.session,
        case_id="case_a",
        baseline="main",
    )


def test_navigation_and_workout_actions_call_pom_methods() -> None:
    ctx = make_context()
    registry = create_default_registry()

    registry.call("navigation.open_widget", ctx)
    registry.call("navigation.back_to_watchface", ctx)
    registry.call("navigation.open_workout", ctx)
    registry.call("workout.pause_or_resume", ctx)
    registry.call("workout.stop", ctx)

    assert ctx.dsl.watchface.calls == [
        ("open_widget", "case_a"),
        ("open_workout", "case_a"),
    ]
    assert ctx.dsl.widget.calls == [("go_back", "case_a")]
    assert ctx.dsl.workout.calls == [
        ("pause_or_resume", "case_a"),
        ("stop", "case_a"),
    ]


def test_navigation_and_workout_actions_record_business_steps() -> None:
    ctx = make_context()
    registry = create_default_registry()

    registry.call("navigation.open_widget", ctx)
    registry.call("navigation.back_to_watchface", ctx)
    registry.call("navigation.open_workout", ctx)
    registry.call("workout.pause_or_resume", ctx)
    registry.call("workout.stop", ctx)

    assert ctx.session.steps == [
        ("case_a", "navigation_open_widget", "passed", {}),
        ("case_a", "navigation_back_to_watchface", "passed", {}),
        ("case_a", "navigation_open_workout", "passed", {}),
        ("case_a", "workout_pause_or_resume", "passed", {}),
        ("case_a", "workout_stop", "passed", {}),
    ]


def test_capture_actions_return_structured_state() -> None:
    ctx = make_context()
    registry = create_default_registry()

    page = registry.call("capture.current_page", ctx)
    widget = registry.call("capture.current_widget", ctx)
    workout = registry.call("capture.workout_state", ctx)

    assert page == PageState(name="main", raw={"Content": "main"})
    assert widget == WidgetState(
        name="/_watch-face(c)/main",
        path="/_watch-face(c)/main",
        raw={"Content": "/_watch-face(c)/main"},
    )
    assert workout == WorkoutState(status="ready", raw={"Content": "ready"})


def test_capture_actions_record_business_steps() -> None:
    ctx = make_context()
    registry = create_default_registry()

    registry.call("capture.current_page", ctx)
    registry.call("capture.current_widget", ctx)
    registry.call("capture.workout_state", ctx)

    assert ctx.session.steps == [
        (
            "case_a",
            "capture_current_page",
            "passed",
            {"page": {"name": "main", "raw": {"Content": "main"}}},
        ),
        (
            "case_a",
            "capture_current_widget",
            "passed",
            {
                "widget": {
                    "name": "/_watch-face(c)/main",
                    "path": "/_watch-face(c)/main",
                    "raw": {"Content": "/_watch-face(c)/main"},
                }
            },
        ),
        (
            "case_a",
            "capture_workout_state",
            "passed",
            {"workout": {"status": "ready", "raw": {"Content": "ready"}}},
        ),
    ]


def test_assertion_actions_record_assertions() -> None:
    ctx = make_context()
    registry = create_default_registry()

    registry.call("assert.equals", ctx, actual="main", expected="main")
    registry.call("assert.not_equals", ctx, actual="widget", expected="main")
    registry.call("assert.non_empty", ctx, actual="ready")
    registry.call("assert.changed", ctx, actual="after", **{"from": "before"})
    registry.call("assert.contains", ctx, actual=["a", "b"], expected="b")

    assert [item[1] for item in ctx.session.assertions] == [
        "assert_equals",
        "assert_not_equals",
        "assert_non_empty",
        "assert_changed",
        "assert_contains",
    ]


def test_assertion_actions_record_structured_states_as_json_safe_values() -> None:
    ctx = make_context()
    registry = create_default_registry()

    registry.call(
        "assert.changed",
        ctx,
        actual=WidgetState(name="weather", path="/widgets/weather", raw={"Content": "weather"}),
        **{
            "from": WidgetState(
                name="main",
                path="/_watch-face(c)/main",
                raw={"Content": "main"},
            )
        },
    )

    assertion = ctx.session.assertions[-1]
    assert assertion[3] == {
        "name": "weather",
        "path": "/widgets/weather",
        "raw": {"Content": "weather"},
    }
    assert assertion[4] == {
        "operator": "!=",
        "value": {
            "name": "main",
            "path": "/_watch-face(c)/main",
            "raw": {"Content": "main"},
        },
    }


def test_assertion_action_failure_raises_assertion_error() -> None:
    ctx = make_context()
    registry = create_default_registry()

    with pytest.raises(AssertionError, match="expected values to be equal"):
        registry.call("assert.equals", ctx, actual="widget", expected="main")


def test_assert_changed_requires_from_parameter() -> None:
    ctx = make_context()
    registry = create_default_registry()

    with pytest.raises(ScenarioActionError, match="assert.changed requires 'from'"):
        registry.call("assert.changed", ctx, actual="after")

    assert ctx.session.assertions == []


def test_assert_contains_requires_string_or_container_actual() -> None:
    ctx = make_context()
    registry = create_default_registry()

    with pytest.raises(
        ScenarioActionError,
        match="assert.contains requires actual to be a string or container",
    ):
        registry.call("assert.contains", ctx, actual=42, expected=4)

    assert ctx.session.assertions == []
