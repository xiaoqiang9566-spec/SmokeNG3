from __future__ import annotations

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.context import ScenarioContext


def pause_or_resume(ctx: ScenarioContext) -> None:
    ctx.dsl.workout.pause_or_resume(ctx.case_id)
    ctx.session.record_step(ctx.case_id, "workout_pause_or_resume", "passed")


def stop(ctx: ScenarioContext) -> None:
    ctx.dsl.workout.stop(ctx.case_id)
    ctx.session.record_step(ctx.case_id, "workout_stop", "passed")


def register_workout_actions(registry: ActionRegistry) -> None:
    registry.register("workout.pause_or_resume", pause_or_resume)
    registry.register("workout.stop", stop)
