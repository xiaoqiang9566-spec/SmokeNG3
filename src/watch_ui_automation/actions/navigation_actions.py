from __future__ import annotations

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.context import ScenarioContext


def open_widget(ctx: ScenarioContext) -> None:
    ctx.dsl.watchface.open_widget(ctx.case_id)
    ctx.session.record_step(ctx.case_id, "navigation_open_widget", "passed")


def open_workout(ctx: ScenarioContext) -> None:
    ctx.dsl.watchface.open_workout(ctx.case_id)
    ctx.session.record_step(ctx.case_id, "navigation_open_workout", "passed")


def back_to_watchface(ctx: ScenarioContext) -> None:
    ctx.dsl.widget.go_back(ctx.case_id)
    ctx.session.record_step(ctx.case_id, "navigation_back_to_watchface", "passed")


def register_navigation_actions(registry: ActionRegistry) -> None:
    registry.register("navigation.open_widget", open_widget)
    registry.register("navigation.open_workout", open_workout)
    registry.register("navigation.back_to_watchface", back_to_watchface)
