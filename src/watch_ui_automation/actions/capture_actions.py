from __future__ import annotations

from dataclasses import asdict

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.context import ScenarioContext
from watch_ui_automation.scenarios.models import PageState, WidgetState, WorkoutState


def current_page(ctx: ScenarioContext) -> PageState:
    payload = ctx.session.read_json(ctx.dsl.resources["current_page"])
    content = payload.get("Content")
    state = PageState(name=str(content), raw=payload)
    ctx.session.record_step(
        ctx.case_id,
        "capture_current_page",
        "passed",
        page=asdict(state),
    )
    return state


def current_widget(ctx: ScenarioContext) -> WidgetState:
    name = ctx.dsl.widget.current_name()
    state = WidgetState(name=name, path=name, raw={"Content": name})
    ctx.session.record_step(
        ctx.case_id,
        "capture_current_widget",
        "passed",
        widget=asdict(state),
    )
    return state


def workout_state(ctx: ScenarioContext) -> WorkoutState:
    status = ctx.dsl.workout.state()
    state = WorkoutState(status=status, raw={"Content": status})
    ctx.session.record_step(
        ctx.case_id,
        "capture_workout_state",
        "passed",
        workout=asdict(state),
    )
    return state


def register_capture_actions(registry: ActionRegistry) -> None:
    registry.register("capture.current_page", current_page)
    registry.register("capture.current_widget", current_widget)
    registry.register("capture.workout_state", workout_state)
