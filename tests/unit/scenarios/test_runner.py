import pytest

from watch_ui_automation.actions import create_default_registry
from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.errors import ScenarioStepError
from watch_ui_automation.scenarios.models import ScenarioCase, ScenarioStep
from watch_ui_automation.scenarios.runner import run_case


class FakeCaseContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeSession:
    def __init__(self) -> None:
        self.steps = []

    def case(self, case_name: str, expected_page: str) -> FakeCaseContext:
        self.steps.append((case_name, "case", expected_page))
        return FakeCaseContext()

    def record_step(self, case_name: str, name: str, status: str, **extra) -> None:
        self.steps.append((case_name, name, status, extra))


def test_run_case_executes_steps_in_order_and_saves_variables() -> None:
    session = FakeSession()
    ctx = ScenarioContext(
        dsl=object(),
        session=session,
        case_id="case_a",
        baseline="main",
    )
    registry = ActionRegistry()
    calls = []

    def capture(ctx):
        calls.append("capture")
        return {"name": "main"}

    def assert_equals(ctx, *, actual, expected):
        calls.append((actual, expected))

    registry.register("capture.current_page", capture)
    registry.register("assert.equals", assert_equals)
    case = ScenarioCase(
        id="case_a",
        title="Case A",
        markers=["yaml"],
        baseline="main",
        steps=[
            ScenarioStep(
                name="capture",
                action="capture.current_page",
                params={},
                save_as="page",
            ),
            ScenarioStep(
                name="assert",
                action="assert.equals",
                params={"actual": "${page.name}", "expected": "main"},
            ),
        ],
        source_file="case.yaml",
    )

    run_case(case, ctx, registry)

    assert calls == ["capture", ("main", "main")]
    assert ctx.variables["page"] == {"name": "main"}
    assert ("case_a", "yaml_step_start", "running", {"step_index": 1, "step_name": "capture", "action": "capture.current_page"}) in session.steps
    assert ("case_a", "yaml_step_end", "passed", {"step_index": 2, "step_name": "assert", "action": "assert.equals"}) in session.steps


def test_run_case_wraps_action_errors_with_step_location() -> None:
    session = FakeSession()
    ctx = ScenarioContext(
        dsl=object(),
        session=session,
        case_id="case_a",
        baseline="main",
    )
    registry = ActionRegistry()

    def explode(ctx):
        raise RuntimeError("boom")

    registry.register("bad.action", explode)
    case = ScenarioCase(
        id="case_a",
        title="Case A",
        markers=["yaml"],
        baseline="main",
        steps=[ScenarioStep(name="explode", action="bad.action", params={})],
        source_file="case.yaml",
    )

    with pytest.raises(ScenarioStepError) as exc_info:
        run_case(case, ctx, registry)

    message = str(exc_info.value)
    assert "file: case.yaml" in message
    assert "case: case_a" in message
    assert "step: 1 - explode" in message
    assert "action: bad.action" in message
    assert "cause: RuntimeError: boom" in message


def test_run_case_rejects_unsupported_saved_result_type() -> None:
    session = FakeSession()
    ctx = ScenarioContext(
        dsl=object(),
        session=session,
        case_id="case_a",
        baseline="main",
    )
    registry = ActionRegistry()

    class UnsupportedResult:
        pass

    registry.register("capture.unsupported", lambda ctx: UnsupportedResult())
    case = ScenarioCase(
        id="case_a",
        title="Case A",
        markers=["yaml"],
        baseline="main",
        steps=[
            ScenarioStep(
                name="capture unsupported",
                action="capture.unsupported",
                params={},
                save_as="bad_result",
            )
        ],
        source_file="case.yaml",
    )

    with pytest.raises(ScenarioStepError) as exc_info:
        run_case(case, ctx, registry)

    assert "Unsupported action result type" in str(exc_info.value)


def test_run_case_rejects_nested_unsupported_saved_result_type() -> None:
    session = FakeSession()
    ctx = ScenarioContext(
        dsl=object(),
        session=session,
        case_id="case_a",
        baseline="main",
    )
    registry = ActionRegistry()

    class UnsupportedResult:
        pass

    registry.register(
        "capture.unsupported_nested",
        lambda ctx: {"nested": [UnsupportedResult()]},
    )
    case = ScenarioCase(
        id="case_a",
        title="Case A",
        markers=["yaml"],
        baseline="main",
        steps=[
            ScenarioStep(
                name="capture unsupported nested",
                action="capture.unsupported_nested",
                params={},
                save_as="bad_result",
            )
        ],
        source_file="case.yaml",
    )

    with pytest.raises(ScenarioStepError) as exc_info:
        run_case(case, ctx, registry)

    message = str(exc_info.value)
    assert "Unsupported action result type" in message
    assert "UnsupportedResult" in message
    assert "step: 1 - capture unsupported nested" in message
    assert "bad_result" not in ctx.variables


def test_run_case_wraps_default_action_parameter_errors_with_step_location() -> None:
    session = FakeSession()
    ctx = ScenarioContext(
        dsl=object(),
        session=session,
        case_id="case_a",
        baseline="main",
    )
    case = ScenarioCase(
        id="case_a",
        title="Case A",
        markers=["yaml"],
        baseline="main",
        steps=[
            ScenarioStep(
                name="changed without baseline",
                action="assert.changed",
                params={"actual": "after"},
            )
        ],
        source_file="case.yaml",
    )

    with pytest.raises(ScenarioStepError) as exc_info:
        run_case(case, ctx, create_default_registry())

    message = str(exc_info.value)
    assert "case: case_a" in message
    assert "step: 1 - changed without baseline" in message
    assert "action: assert.changed" in message
    assert "cause: ScenarioActionError: assert.changed requires 'from'" in message
